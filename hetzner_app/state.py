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
        })

    # Angeheftetes zuerst, darin das zuletzt Benutzte oben.
    result.sort(key=lambda s: (not s["pinned"], -s["lastActivity"]))
    return result
