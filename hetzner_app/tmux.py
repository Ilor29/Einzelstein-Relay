"""Alles, was mit tmux zu tun hat.

Die Sitzungen leben in tmux, nicht in diesem Dienst. Startet der Dienst neu,
laufen die Sitzungen weiter — genau deshalb kann man am Rechner anfangen und
am Handy weitermachen.
"""

from __future__ import annotations

import asyncio
import shlex
import subprocess
import time
from dataclasses import dataclass

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
SERVER = ["-L", "hz"]

# Trennt die Felder in der tmux-Ausgabe. Ein Zeichen, das in Sitzungsnamen
# und Pfaden nicht vorkommt.
SEP = "\x1f"


class TmuxError(RuntimeError):
    pass


@dataclass
class TmuxSession:
    name: str          # ohne Präfix, so wie der Benutzer sie nennt
    cwd: str
    created: int       # Unix-Zeit
    last_activity: int
    attached: bool


def _run(*args: str) -> str:
    result = subprocess.run(
        ["tmux", *SERVER, *args],
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


def list_sessions() -> list[TmuxSession]:
    fmt = SEP.join([
        "#{session_name}",
        "#{session_path}",
        "#{session_created}",
        "#{session_activity}",
        "#{session_attached}",
    ])
    out = _run("list-sessions", "-F", fmt)

    sessions = []
    for line in out.splitlines():
        if not line.strip():
            continue
        name, path, created, activity, attached = line.split(SEP)
        if not name.startswith(PREFIX):
            continue
        sessions.append(TmuxSession(
            name=name[len(PREFIX):],
            cwd=path,
            created=int(created),
            last_activity=int(activity),
            attached=attached != "0",
        ))
    return sessions


def exists(name: str) -> bool:
    return any(s.name == name for s in list_sessions())


def create(name: str, cwd: str, first_prompt: str | None = None) -> None:
    """Startet Claude Code in einer neuen, dauerhaften tmux-Sitzung."""
    if exists(name):
        raise TmuxError(f"Eine Sitzung namens {name!r} läuft bereits.")

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
        "claude",
    )

    # Damit mehrere Zuschauer (Handy und Rechner) unterschiedlich große
    # Fenster haben dürfen, ohne dass der kleinste alle anderen erdrosselt.
    _run("set-option", "-t", PREFIX + name, "aggressive-resize", "on")

    if first_prompt:
        # Claude Code braucht einen Moment, bis es Eingaben annimmt.
        # Das erledigt der Aufrufer über send_text(), nicht wir hier —
        # siehe server.py, wo darauf gewartet wird.
        pass


def kill(name: str) -> None:
    _run("kill-session", "-t", PREFIX + name)


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


def send_text(name: str, text: str) -> None:
    """Schickt Text an die Sitzung, so als hätte man ihn getippt."""
    _run("send-keys", "-t", PREFIX + name, "-l", text)


def send_key(name: str, key: str) -> None:
    """Schickt eine Sondertaste, z.B. 'Enter', 'Escape', 'C-c', 'Up'."""
    _run("send-keys", "-t", PREFIX + name, key)


def capture(name: str, lines: int | None = 200) -> str:
    """Liest den Inhalt der Sitzung als Text.

    Mit `lines` bekommst du so viele Zeilen Verlauf dazu — das brauchen wir
    fürs Vorlesen. Mit `lines=None` nur den sichtbaren Bildschirm, und das ist
    der entscheidende Unterschied: Nur dort verrät die Fußzeile, ob Claude
    gerade arbeitet. Im Verlauf stehen alte Kreisel-Zeilen für immer herum
    und würden jede Sitzung auf ewig als "läuft" ausweisen.
    """
    args = ["capture-pane", "-p", "-t", PREFIX + name]
    if lines is not None:
        args += ["-S", f"-{lines}"]
    return _run(*args)


async def attach(name: str, cols: int, rows: int) -> asyncio.subprocess.Process:
    """Bindet sich an eine Sitzung an und liefert den Prozess zurück.

    Die Ein- und Ausgabe läuft über Pipes; der Aufrufer verbindet sie mit dem
    WebSocket. Jeder Zuschauer bekommt seinen eigenen Anbindungs-Prozess.
    """
    # Ohne echtes Terminal wüsste tmux die Fenstergröße nicht. Wir schummeln
    # eins herbei, indem wir die Größe explizit mitgeben.
    cmd = (
        f"stty cols {int(cols)} rows {int(rows)}; "
        f"exec tmux {' '.join(SERVER)} attach-session -t {shlex.quote(PREFIX + name)}"
    )
    return await asyncio.create_subprocess_exec(
        "script", "-q", "-c", cmd, "/dev/null",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )


def resize(name: str, cols: int, rows: int) -> None:
    _run("resize-window", "-t", PREFIX + name, "-x", str(cols), "-y", str(rows))
