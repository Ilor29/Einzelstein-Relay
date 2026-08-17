"""Alles, was mit tmux zu tun hat.

Die Sitzungen leben in tmux, nicht in diesem Dienst. Startet der Dienst neu,
laufen die Sitzungen weiter — genau deshalb kann man am Rechner anfangen und
am Handy weitermachen.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path

# tmux-Sitzungen dieser App tragen alle dieses Präfix, damit wir fremde
# tmux-Sitzungen des Benutzers nicht anfassen.
PREFIX = "hz-"

# Unser eigener tmux-Server.
#
# Ohne das erbt tmux den Server dessen, der es gerade aufruft — und Claude Code
# läuft selbst in tmux. Ruft man tmux von dort aus auf, landet die Sitzung auf
# einem ganz anderen Server als dem, in dem der Dienst nachsieht. Genau daran
# ist die App zuerst gescheitert: Die Sitzungen waren da, nur eben woanders.
#
# Mit einem festen Namen sehen Dienst, Skripte und Handy immer dasselbe.
SOCKET = "hz"

# Trennt die Felder in der tmux-Ausgabe. Ein Zeichen, das in Sitzungsnamen
# und Pfaden nicht vorkommt.
SEP = "\x1f"


class TmuxError(RuntimeError):
    pass


@dataclass
class TmuxSession:
    name: str          # so, wie die App sie nennt (die "Kennung")
    cwd: str
    created: int       # Unix-Zeit
    last_activity: int
    attached: bool
    eigen: bool = True  # von dieser App angelegt — oder eine fremde Sitzung?


def _sockets() -> list[str]:
    """Alle tmux-Server dieses Benutzers.

    Nicht nur unserer: Auf dem Server laufen auch andere tmux-Sitzungen — die,
    in der Claude Code selbst sitzt, zum Beispiel. Die will man am Handy
    genauso öffnen und vorlesen lassen können.
    """
    ordner = Path(f"/tmp/tmux-{os.getuid()}")
    if not ordner.is_dir():
        return []
    return sorted(p.name for p in ordner.iterdir() if p.is_socket())


def _zerlegen(kennung: str) -> tuple[str, str]:
    """Aus der Kennung der App wird ein tmux-Server und ein Sitzungsname.

    Eigene Sitzungen heißen schlicht "willkommen" und liegen auf unserem
    Server unter "hz-willkommen". Fremde tragen ihren Server im Namen:
    "hetzner-app:claude".
    """
    if ":" in kennung:
        socket, name = kennung.split(":", 1)
        return socket, name
    return SOCKET, PREFIX + kennung


def _run(*args: str, socket: str = SOCKET) -> str:
    result = subprocess.run(
        ["tmux", "-L", socket, *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        # Läuft noch kein tmux-Server, ist das kein Fehler, sondern heißt
        # schlicht: keine Sitzungen. Beim ersten Start ist das der Normalfall.
        # Kleingeschrieben verglichen — tmux formuliert es mal so, mal so.
        harmlos = ("no server running", "no such file or directory")
        if any(satz in stderr.lower() for satz in harmlos):
            return ""
        raise TmuxError(f"tmux {' '.join(args)}: {stderr}")
    return result.stdout


def list_sessions(auch_fremde: bool = True) -> list[TmuxSession]:
    """Alle Sitzungen — unsere eigenen und, wenn gewünscht, auch die fremden.

    Fremd sind zum Beispiel die Sitzungen, in denen Claude Code selbst läuft.
    Auch die will man am Handy öffnen und sich vorlesen lassen können.
    """
    fmt = SEP.join([
        "#{session_name}",
        # Der Ordner, in dem gerade gearbeitet wird — nicht der, in dem die
        # Sitzung einst erzeugt wurde. Bei fremden Sitzungen ist Letzterer
        # oft schlicht "/", und dann legt man Dateien im Wurzelverzeichnis an.
        "#{pane_current_path}",
        "#{session_created}",
        "#{session_activity}",
        "#{session_attached}",
    ])

    sessions: list[TmuxSession] = []
    sockets = _sockets() if auch_fremde else [SOCKET]

    for socket in sockets:
        try:
            out = _run("list-sessions", "-F", fmt, socket=socket)
        except TmuxError:
            continue

        for line in out.splitlines():
            if not line.strip():
                continue
            try:
                name, path, created, activity, attached = line.split(SEP)
            except ValueError:
                continue

            eigen = socket == SOCKET and name.startswith(PREFIX)
            if eigen:
                kennung = name[len(PREFIX):]
            elif socket == SOCKET:
                continue           # auf unserem Server nur unsere Sitzungen
            else:
                kennung = f"{socket}:{name}"

            sessions.append(TmuxSession(
                name=kennung,
                cwd=path,
                created=int(created),
                last_activity=int(activity),
                attached=attached != "0",
                eigen=eigen,
            ))

    return sessions


def exists(name: str) -> bool:
    return any(s.name == name for s in list_sessions())


def create(
    name: str,
    cwd: str,
    first_prompt: str | None = None,
    ohne_rueckfragen: bool = False,
    fortsetzen: bool = False,
) -> None:
    """Startet Claude Code in einer neuen, dauerhaften tmux-Sitzung.

    Mit ohne_rueckfragen läuft Claude im Modus "fragt nie" — er führt auch
    Befehle ohne Rückfrage aus. Das lässt sich nur beim Start setzen, nicht
    später umschalten, darum steckt es hier.

    Mit fortsetzen wacht eine schlafen gelegte Sitzung wieder auf: Claude
    setzt das jüngste Gespräch dieses Ordners fort (--continue), statt leer
    anzufangen. Gibt es dort noch gar kein Gespräch, schlägt --continue fehl —
    dafür steht der Rückfall dahinter: dann eben frisch. tmux reicht die eine
    Befehlszeile an die Shell durch, darum funktioniert das ||.
    """
    if exists(name):
        raise TmuxError(f"Eine Sitzung namens {name!r} läuft bereits.")

    befehl = "claude --dangerously-skip-permissions" if ohne_rueckfragen else "claude"
    if fortsetzen:
        befehl = f"{befehl} --continue || {befehl}"

    _run(
        "new-session",
        "-d",                     # im Hintergrund, wir binden uns später an
        "-s", PREFIX + name,
        "-c", cwd,
        # Breit genug, dass Claude Code seine Statuszeile ausschreibt. Bei
        # 80 Zeichen kürzt es sie, und dann sehen wir nicht mehr, ob es
        # gerade arbeitet oder auf eine Antwort wartet.
        "-x", "120",
        "-y", "40",
        befehl,
    )

    # Damit mehrere Zuschauer (Handy und Rechner) unterschiedlich große
    # Fenster haben dürfen, ohne dass der kleinste alle anderen erdrosselt.
    _run("set-option", "-t", PREFIX + name, "aggressive-resize", "on", socket=SOCKET)

    # tmux' eigene Statusleiste ausblenden. Auf dem Handy ist jede Zeile
    # kostbar, und was sie anzeigt — Sitzungsname und Uhrzeit — steht in der
    # App ohnehin schon oben drüber.
    _run("set-option", "-t", PREFIX + name, "status", "off", socket=SOCKET)

    # Viel Verlauf aufheben. tmux merkt sich sonst nur 2000 Zeilen, und die
    # sind bei Claude Code in einer halben Stunde voll — dann kann man nicht
    # mehr nachlesen, was vorhin besprochen wurde.
    _run("set-option", "-t", PREFIX + name, "history-limit", "50000", socket=SOCKET)

    if first_prompt:
        # Claude Code braucht einen Moment, bis es Eingaben annimmt.
        # Das erledigt der Aufrufer über send_text(), nicht wir hier —
        # siehe server.py, wo darauf gewartet wird.
        pass


def kill(name: str) -> None:
    socket, sitzung = _zerlegen(name)
    _run("kill-session", "-t", sitzung, socket=socket)


def warte_bis_bereit(name: str, sekunden: float = 30) -> bool:
    """Wartet, bis Claude Code seine Eingabezeile zeigt.

    Schickt man den ersten Auftrag zu früh, tippt man gegen ein Programm, das
    noch startet — der Text landet im Nichts, und die Sitzung steht mit leerem
    Bildschirm da.
    """
    frist = time.monotonic() + sekunden
    while time.monotonic() < frist:
        try:
            if "❯" in capture(name, lines=None):
                return True
        except TmuxError:
            pass
        time.sleep(0.4)
    return False


def dialog_zustand(name: str) -> str:
    """Liegt gerade ein Auswahl-Dialog über der Eingabe?

    Claude Code legt gelegentlich einen Dialog über das Eingabefeld — die
    Einrichtungsfrage zum Auto-Modus etwa, oder die Vertrauensfrage beim
    ersten Öffnen eines Ordners. Solange so ein Dialog offen ist, landet
    alles, was die App tippt, im Dialog statt im Gespräch: Der Text
    versickert, das Enter klickt womöglich etwas an. Genau so hat der
    Brain-Chat am 17.08. Nachrichten verschluckt, ohne dass es wer merkte.

    Drei Antworten:
      "frei"       — die normale Eingabezeile, senden ist sicher.
      "abbrechbar" — ein Dialog, der laut eigener Fußzeile gefahrlos mit
                     Escape zu schließen ist ("Esc to cancel").
      "blockiert"  — ein Dialog, bei dem Escape schaden könnte (die
                     Vertrauensfrage etwa beendet bei Escape gleich ganz
                     Claude). Den muss ein Mensch beantworten.
    """
    try:
        schirm = capture(name, lines=None)
    except TmuxError:
        return "frei"
    # Nur der untere Rand zählt: Dort schreiben Dialoge ihre Tastenhilfe
    # hin. Weiter oben steht Gesprächstext, und der darf diese Worte
    # zitieren, ohne dass wir einen Dialog wittern.
    fuss = "\n".join(schirm.rstrip().splitlines()[-12:]).lower()
    if "shift+tab to cycle" in fuss:
        return "frei"  # die normale Statuszeile — kein Dialog liegt davor
    if "esc to cancel" in fuss:
        return "abbrechbar"
    if "enter to continue" in fuss or "enter to confirm" in fuss:
        return "blockiert"
    return "frei"


# Ein einzelnes send-keys-Argument kappt der Kernel bei rund 128 KB
# (MAX_ARG_STRLEN). Ein langer Text — etwa ein eingefügter Artikel — scheiterte
# dann mit "Argument list too long", und der Aufrufer bekam einen 500er. Darum
# zerlegen wir in Stücke. 8000 Zeichen sind selbst bei 4 Byte je Zeichen noch
# weit unter der Grenze.
_SENDE_STUECK = 8000

# Ein Text, ein Stück Arbeit: Ohne die Sperre könnten zwei gleichzeitige
# Sende-Aufrufe (Eingabe + Schnellbefehl, zwei Geräte) ihre Stücke im
# Eingabepuffer verzahnen — und bei Claude käme ein zusammengewürfelter Text
# an. Vor der Stückelung war ein Senden ein einziger tmux-Aufruf und damit
# von selbst atomar; die Sperre stellt genau das wieder her.
_sende_sperre = threading.Lock()


def send_text(name: str, text: str) -> None:
    """Schickt Text an die Sitzung, so als hätte man ihn getippt.

    Auch sehr lange Texte: Sie werden in Stücke zerlegt und nacheinander
    geschickt — tmux reiht sie im Eingabepuffer nahtlos aneinander, das Ergebnis
    ist dasselbe, als käme alles auf einmal. Zerteilt wird nach Zeichen, nie
    mitten in einem Mehr-Byte-Zeichen.
    """
    if not text:
        return
    socket, sitzung = _zerlegen(name)
    with _sende_sperre:
        for anfang in range(0, len(text), _SENDE_STUECK):
            stueck = text[anfang:anfang + _SENDE_STUECK]
            _run("send-keys", "-t", sitzung, "-l", stueck, socket=socket)


def send_key(name: str, key: str) -> None:
    """Schickt eine Sondertaste, z.B. 'Enter', 'Escape', 'C-c', 'Up'."""
    socket, sitzung = _zerlegen(name)
    _run("send-keys", "-t", sitzung, key, socket=socket)


def capture(name: str, lines: int | None = 200, verbunden: bool = False) -> str:
    """Liest den Inhalt der Sitzung als Text.

    Mit `lines` bekommst du so viele Zeilen Verlauf dazu — das brauchen wir
    fürs Vorlesen. Mit `lines=None` nur den sichtbaren Bildschirm, und das ist
    der entscheidende Unterschied: Nur dort verrät die Fußzeile, ob Claude
    gerade arbeitet. Im Verlauf stehen alte Kreisel-Zeilen für immer herum
    und würden jede Sitzung auf ewig als "läuft" ausweisen.

    Mit `verbunden` fügt tmux umbrochene Zeilen wieder zusammen (-J). Das
    braucht, wer nach etwas sucht, das länger ist als eine Terminalzeile —
    eine lange Web-Adresse etwa zerfällt sonst in zwei Hälften, und kein
    Muster der Welt findet sie wieder.
    """
    socket, sitzung = _zerlegen(name)
    args = ["capture-pane", "-p", "-t", sitzung]
    if verbunden:
        args.append("-J")
    if lines is not None:
        args += ["-S", f"-{lines}"]
    return _run(*args, socket=socket)


async def attach(name: str, cols: int, rows: int) -> asyncio.subprocess.Process:
    """Bindet sich an eine Sitzung an und liefert den Prozess zurück.

    Die Ein- und Ausgabe läuft über Pipes; der Aufrufer verbindet sie mit dem
    WebSocket. Jeder Zuschauer bekommt seinen eigenen Anbindungs-Prozess.
    """
    socket, sitzung = _zerlegen(name)

    # Ohne echtes Terminal wüsste tmux die Fenstergröße nicht. Wir schummeln
    # eins herbei, indem wir die Größe explizit mitgeben.
    cmd = (
        f"stty cols {int(cols)} rows {int(rows)}; "
        f"exec tmux -L {shlex.quote(socket)} attach-session -t {shlex.quote(sitzung)}"
    )

    # TERM sagt tmux, was für ein Terminal am anderen Ende sitzt. Fehlt es,
    # weiß tmux nicht, wie es den Bildschirm zeichnen soll, und bricht mit
    # "terminal does not support clear" ab — der Dienst läuft nämlich unter
    # systemd, und das setzt kein TERM. Im Browser sitzt xterm.js, also sagen
    # wir genau das.
    umgebung = {**os.environ, "TERM": "xterm-256color"}

    return await asyncio.create_subprocess_exec(
        "script", "-q", "-c", cmd, "/dev/null",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=umgebung,
    )


def resize(name: str, cols: int, rows: int) -> None:
    socket, sitzung = _zerlegen(name)
    # Fremde Sitzungen nicht umgrößen: Dort sitzt womöglich noch jemand am
    # Rechner davor, und dem würde der Bildschirm unter den Händen wegrutschen.
    if socket != SOCKET:
        return
    _run("resize-window", "-t", sitzung, "-x", str(cols), "-y", str(rows), socket=socket)
