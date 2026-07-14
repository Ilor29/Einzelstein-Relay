"""Was tmux nicht weiß: angeheftet oder nicht, und wie es der Sitzung geht.

tmux kennt nur Sitzungen. Das Anheften und die Zustandsanzeige sind unsere
Zutat — sie liegen in einer schlichten JSON-Datei neben den Sitzungen.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import tmux, tts

STATE_FILE = Path.home() / ".hetzner-app" / "sitzungen.json"

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
    return {name: Meta(**values) for name, values in raw.items()}


def _save(metas: dict[str, Meta]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(
        {name: asdict(m) for name, m in metas.items()},
        indent=2,
        ensure_ascii=False,
    ))
    tmp.replace(STATE_FILE)  # atomar, damit bei einem Absturz nichts halb dasteht


def get(name: str) -> Meta:
    return _load().get(name, Meta())


def update(name: str, **changes) -> Meta:
    metas = _load()
    meta = metas.get(name, Meta())
    for key, value in changes.items():
        setattr(meta, key, value)
    metas[name] = meta
    _save(metas)
    return meta


def forget(name: str) -> None:
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
_MOEGLICHKEIT = re.compile(r"^[❯>»\s]*(\d+)\.\s+(.+?)$")


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
    """Alles, was die Sitzungsübersicht im Handy braucht — in einem Rutsch."""
    metas = _load()
    now = int(time.time())
    result = []

    for session in tmux.list_sessions():
        meta = metas.get(session.name, Meta())
        state = detect(session.name)

        result.append({
            "name": session.name,
            "cwd": session.cwd,
            "pinned": meta.pinned,
            "notifyWhenDone": meta.notify_when_done,
            "state": state,
            "preview": preview(session.name),
            "lastActivity": session.last_activity,
            "idleSeconds": now - session.last_activity,
            "attached": session.attached,
            # Fremde Sitzungen — etwa die, in der Claude Code selbst läuft —
            # darf man ansehen und bedienen, aber nicht beenden.
            "eigen": session.eigen,
            "modell": meta.modell,
        })

    # Angeheftetes zuerst, darin das zuletzt Benutzte oben.
    result.sort(key=lambda s: (not s["pinned"], -s["lastActivity"]))
    return result
