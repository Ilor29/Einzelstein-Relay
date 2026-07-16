"""Was tmux nicht weiß: angeheftet oder nicht, und wie es der Sitzung geht.

tmux kennt nur Sitzungen. Das Anheften und die Zustandsanzeige sind unsere
Zutat — sie liegen in einer schlichten JSON-Datei neben den Sitzungen.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field, fields
from pathlib import Path

from . import tmux, tts

STATE_FILE = Path.home() / ".hetzner-app" / "sitzungen.json"

# Schützt die Lese-ändern-Schreib-Zyklen. Ohne die Sperre könnten zwei
# gleichzeitige update()-Aufrufe einander überschreiben — eine Änderung
# (z. B. „angeheftet") ginge verloren.
_sperre = threading.Lock()

# Zustände, die wir in der Übersicht anzeigen.
RUNNING = "running"   # Claude arbeitet gerade
WAITING = "waiting"   # Claude wartet auf eine Antwort von dir
IDLE = "idle"         # nichts los


@dataclass
class Meta:
    pinned: bool = False
    notify_when_done: bool = False
    created_prompt: str = ""
    # Welches Modell wir zuletzt gewählt haben. Claude Code sagt es uns nicht,
    # also merken wir es uns selbst.
    modell: str = ""
    # Wie die Sitzung im Handy heißen soll. Leer heißt: ihr technischer Name.
    # Der bleibt unangetastet — an ihm hängen tmux, der Ordner und die
    # Mitschrift. Wir benennen nur das Schild an der Tür um, nicht das Haus.
    anzeige: str = ""
    # Zuletzt gesehener Zustand — damit wir merken, wenn RUNNING zu WAITING
    # wird, und dann eine Benachrichtigung schicken können.
    last_state: str = IDLE
    tags: list[str] = field(default_factory=list)


def _load() -> dict[str, Meta]:
    if not STATE_FILE.exists():
        return {}
    try:
        raw = json.loads(STATE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        # Kaputte Datei darf die App nicht lahmlegen; wir fangen neu an.
        return {}

    # Felder, die es einmal gab und nicht mehr gibt, überlesen wir. Sonst
    # brächte eine alte Zustandsdatei die neue App zu Fall — ausgerechnet beim
    # Aufräumen.
    erlaubt = {f.name for f in fields(Meta)}
    return {
        name: Meta(**{k: v for k, v in values.items() if k in erlaubt})
        for name, values in raw.items()
    }


def _save(metas: dict[str, Meta]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    inhalt = json.dumps(
        {name: asdict(m) for name, m in metas.items()},
        indent=2,
        ensure_ascii=False,
    )
    # Eigene Temp-Datei je Aufruf (nicht ein fester ".tmp"-Name): Sonst schrieben
    # zwei gleichzeitige _save in dieselbe Datei und das replace() könnte einen
    # halb geschriebenen Stand übernehmen.
    fd, tmp = tempfile.mkstemp(dir=STATE_FILE.parent, prefix=STATE_FILE.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(inhalt)
        os.replace(tmp, STATE_FILE)   # atomar, damit bei einem Absturz nichts halb dasteht
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def get(name: str) -> Meta:
    return _load().get(name, Meta())


def update(name: str, **changes) -> Meta:
    with _sperre:
        metas = _load()
        meta = metas.get(name, Meta())
        for key, value in changes.items():
            setattr(meta, key, value)
        metas[name] = meta
        _save(metas)
    return meta


def forget(name: str) -> None:
    with _sperre:
        metas = _load()
        metas.pop(name, None)
        _save(metas)


# --- Zustandserkennung -------------------------------------------------------
#
# Wir lesen den sichtbaren Inhalt der Sitzung und schließen daraus, was los ist.
# Claude Code verrät seinen Zustand recht zuverlässig über ein paar Textmarker.

# Solange Claude arbeitet, bietet die Fußzeile den Abbruch mit Escape an.
# Ist Claude fertig, verschwindet der Hinweis. Ein verlässlicheres Signal
# gibt es nicht — und es steht nur im sichtbaren Bereich, nie im Verlauf.
_ARBEITET = re.compile(r"esc to interrupt", re.IGNORECASE)

# Rückfragen von Claude — Berechtigungen, Ja/Nein, Auswahllisten.
_FRAGT = re.compile(
    r"(Do you want|Would you like|\(y/n\)|❯\s*1\.|Proceed\?|Möchtest du|Soll ich)",
    re.IGNORECASE,
)

# Was die Vorlese-Aufbereitung an Stelle von Code und Werkzeugen einsetzt.
# Fürs Ohr nützlich, als Vorschau nichtssagend.
_PLATZHALTER = re.compile(r"^(Codeblock,|Werkzeug benutzt:|\d+ Werkzeuge)")


def detect(name: str) -> str:
    try:
        # Nur der sichtbare Bildschirm. Im Verlauf stünden alte Kreisel und
        # alte Rückfragen für immer herum, und die Sitzung sähe ewig
        # beschäftigt aus.
        screen = tmux.capture(name, lines=None)
    except tmux.TmuxError:
        return IDLE

    if _ARBEITET.search(screen):
        return RUNNING
    if _FRAGT.search(screen):
        return WAITING
    return IDLE


# Der Rahmen, den Claude Code um seine Rückfragen malt. Fürs Auge im Terminal
# schön, für uns nur Beiwerk — wir wollen die nackte Zeile.
_RAHMEN = re.compile(r"^[\s│┃|╭╰╮╯─━]*|[\s│┃|─━]*$")

# "❯ 1. Yes" — eine Antwortmöglichkeit, wie Claude Code sie anbietet.
#
# Das Leerzeichen nach dem Punkt darf fehlen: die lange "Ja, und nicht mehr
# fragen"-Zeile rendert Claude Code als "2.Yes …", ohne Lücke. Verlangten wir
# hier ein Leerzeichen, fiele bei genau dieser Erlaubnis-Frage eine Antwort
# durchs Raster, es blieben zu wenige übrig — und die App zeigte gar keine
# Knöpfe, obwohl die Sitzung händeringend auf eine Antwort wartet.
_MOEGLICHKEIT = re.compile(r"^[❯>»\s]*(\d+)\.\s*(.+?)$")


def frage(name: str) -> dict | None:
    """Die Rückfrage, an der die Sitzung gerade hängt — samt Antworten.

    Claude Code fragt um Erlaubnis, bevor es Dateien ändert oder Befehle
    ausführt. Im Terminal beantwortet man das mit einer Zifferntaste. Unterwegs
    stand die App bisher einfach still: Sie zeigte "wartet auf dich", aber es
    gab nichts, worauf man hätte tippen können. Also lesen wir die Frage vom
    Bildschirm ab und machen Knöpfe daraus.

    Gibt None zurück, wenn gerade nichts zu beantworten ist.
    """
    try:
        screen = tmux.capture(name, lines=None)
    except tmux.TmuxError:
        return None

    # Arbeitet Claude noch, ist eine Auswahlliste auf dem Schirm bestenfalls
    # ein Überbleibsel von vorhin.
    if _ARBEITET.search(screen):
        return None

    zeilen = [_RAHMEN.sub("", z) for z in screen.splitlines()]

    moeglichkeiten: list[dict] = []
    erste = -1
    gewaehlt = False
    for i, zeile in enumerate(zeilen):
        treffer = _MOEGLICHKEIT.match(zeile)
        if not treffer:
            continue
        nummer = int(treffer.group(1))
        # Eine Liste beginnt bei 1 und zählt lückenlos weiter. Alles andere ist
        # eine Aufzählung in Claudes Fließtext und keine Frage an uns.
        if nummer == 1:
            moeglichkeiten = []
            erste = i
            gewaehlt = False
        if nummer != len(moeglichkeiten) + 1:
            continue
        # Auf genau einer Antwort steht der Auswahlpfeil. Fehlt er ganz, zählt
        # Claude nur etwas auf — dann wären unsere Knöpfe eine Erfindung.
        if "❯" in zeile:
            gewaehlt = True
        moeglichkeiten.append({"nummer": nummer, "text": treffer.group(2).strip()})

    # Eine einzelne Zeile "1. irgendwas" ist keine Auswahl.
    if len(moeglichkeiten) < 2 or not gewaehlt:
        return None

    # Die Frage steht über der ersten Antwort — die letzte Zeile mit Inhalt.
    text = ""
    for zeile in reversed(zeilen[:erste]):
        if zeile.strip():
            text = zeile.strip()
            break

    return {"text": text, "moeglichkeiten": moeglichkeiten}


# Wie viel Kontext dem Gespräch noch bleibt. Claude Code zeigt das nur, wenn es
# knapp wird — "Context left until auto-compact: 18%" oder "18% context left".
# Genau dann ist die Zahl auch interessant: Sie sagt, wann das Gespräch bald
# aufgeräumt (verdichtet) wird. Ist nichts zu sehen, ist reichlich Kontext da.
_KONTEXT = re.compile(r"context[^%\d]{0,30}?(\d{1,3})\s*%|(\d{1,3})\s*%\s*context", re.I)


# Der Berechtigungs-Modus, den Claude Code unten in der Fußzeile anzeigt. Mit
# Shift+Tab schaltet man ihn im Kreis: manual → acceptEdits → plan → auto.
# "bypassPermissions" ("fragt nie") steht nicht im Kreis — das geht nur beim
# Starten der Sitzung, nicht danach.
_MODI = {
    "manual mode on": "manual",
    "accept edits on": "acceptEdits",
    "plan mode on": "plan",
    "auto mode on": "auto",
}


def modus(name: str) -> str | None:
    """Welcher Berechtigungs-Modus gerade läuft — oder None, wenn nichts steht."""
    try:
        screen = tmux.capture(name, lines=None).lower()
    except tmux.TmuxError:
        return None
    for marker, wert in _MODI.items():
        if marker in screen:
            return wert
    return None


def kontext(name: str) -> int | None:
    """Der Kontext-Rest in Prozent — oder None, wenn Claude Code ihn nicht nennt."""
    try:
        screen = tmux.capture(name, lines=None)
    except tmux.TmuxError:
        return None
    treffer = _KONTEXT.search(screen)
    if not treffer:
        return None
    wert = int(treffer.group(1) or treffer.group(2))
    return wert if 0 <= wert <= 100 else None


def preview(name: str, max_len: int = 90) -> str:
    """Die eine Zeile, die in der Übersicht unter dem Sitzungsnamen steht.

    Es ist dieselbe Frage wie beim Vorlesen — was hat Claude zuletzt gesagt? —
    also nehmen wir dieselbe Aufbereitung und daraus den letzten Satz. Was zum
    Vorlesen zu belanglos ist, taugt auch nicht als Vorschau.
    """
    try:
        text = tts.for_speech(tmux.capture(name, lines=200))
    except tmux.TmuxError:
        return ""

    for absatz in reversed(text.splitlines()):
        # "Codeblock, 3 Zeilen" und "Werkzeug benutzt: Read" sind Platzhalter
        # fürs Ohr, keine Aussage fürs Auge.
        if _PLATZHALTER.match(absatz):
            continue
        if absatz.strip():
            return absatz.strip()[:max_len]
    return ""


def overview() -> list[dict]:
    """Alles, was die Sitzungsübersicht im Handy braucht — in einem Rutsch.

    Ein Eintrag je Projekt, nicht je Terminal. Im selben Ordner laufen leicht
    mehrere Sitzungen — eine am Rechner, eine per Fernsteuerung, eine aus dem
    Handy —, und dann stand dasselbe Projekt dreimal untereinander, jedes mit
    einem Bruchstück der Arbeit. Es ist aber ein Projekt und eine Unterhaltung
    (siehe mitschrift.py). Also ein Schild in der Liste.

    Bedient wird darunter ein bestimmtes Terminal: das eigene, sonst das
    zuletzt benutzte. Sein technischer Name steht in "name" — daran hängen alle
    weiteren Aufrufe, vom Tippen bis zum Abbrechen.
    """
    metas = _load()
    now = int(time.time())

    projekte: dict[str, list] = {}
    for session in tmux.list_sessions():
        projekte.setdefault(session.cwd, []).append(session)

    result = []
    for cwd, sitzungen in projekte.items():
        # Wer das Wort führt: unsere eigene Sitzung, sonst die zuletzt benutzte.
        sitzungen.sort(key=lambda s: (not s.eigen, -s.last_activity))
        fuehrend = sitzungen[0]
        eigene_metas = [metas.get(s.name, Meta()) for s in sitzungen]
        meta = eigene_metas[0]

        # Arbeitet irgendwo im Projekt gerade Claude, arbeitet das Projekt.
        zustaende = [detect(s.name) for s in sitzungen]
        zustand = (
            RUNNING if RUNNING in zustaende
            else WAITING if WAITING in zustaende
            else IDLE
        )

        result.append({
            "name": fuehrend.name,
            "cwd": cwd,
            # Angeheftet ist ein Projekt, sobald eines seiner Terminals es ist.
            "pinned": any(m.pinned for m in eigene_metas),
            "notifyWhenDone": any(m.notify_when_done for m in eigene_metas),
            "state": zustand,
            "preview": preview(fuehrend.name),
            "lastActivity": max(s.last_activity for s in sitzungen),
            "idleSeconds": now - max(s.last_activity for s in sitzungen),
            "attached": any(s.attached for s in sitzungen),
            # Fremde Sitzungen — etwa die, in der Claude Code selbst läuft —
            # darf man ansehen und bedienen, aber nicht beenden.
            "eigen": fuehrend.eigen,
            "modell": meta.modell,
            # Der Kontext-Rest, wenn Claude Code ihn nennt — sonst None, dann
            # zeigt das Handy dazu schlicht nichts.
            "kontext": kontext(fuehrend.name),
            # Der Berechtigungs-Modus (fragt / Änderungen ok / Plan / Auto).
            "modus": modus(fuehrend.name),
            # Ohne eigenen Namen heißt der Kanal wie das Projekt, an dem er
            # arbeitet — nicht wie das Terminal, in dem er zufällig läuft.
            "anzeige": meta.anzeige or Path(cwd).name,
            # Wie viele Terminals hinter dem einen Schild stecken.
            "terminals": len(sitzungen),
        })

    # Angeheftetes zuerst, darin das zuletzt Benutzte oben.
    result.sort(key=lambda s: (not s["pinned"], -s["lastActivity"]))
    return result
