"""Entscheidungskorb: Fragen der Karten an Roli, abgelegt vom Brain-Werkzeug
`Brain/werkzeug/korb.py` in `Brain/korb/fragen.json`. Hier wird nur gelesen
und die Antwort festgehalten; zugestellt wird in server.py.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
from pathlib import Path

PFAD = Path(os.environ.get("HETZNER_APP_KORB", Path.home() / "projekte" / "Brain" / "korb" / "fragen.json"))


def _laden() -> dict:
    if not PFAD.exists():
        return {"naechste_id": 1, "fragen": []}
    return json.loads(PFAD.read_text(encoding="utf-8"))


def offene() -> list[dict]:
    try:
        fragen = _laden()["fragen"]
    except (OSError, ValueError, KeyError):
        return []
    return [q for q in fragen if q.get("status") == "offen"]


def antworten(frage_id: int, text: str, zugestellt_fn) -> dict | None:
    """Hält die Antwort fest und ruft zugestellt_fn(frage, text) -> bool.
    Gibt die Frage zurück, oder None, wenn es sie nicht (mehr) offen gibt."""
    sperre = open(str(PFAD) + ".lock", "w")
    fcntl.flock(sperre, fcntl.LOCK_EX)
    try:
        d = _laden()
        for q in d["fragen"]:
            if q["id"] == frage_id and q["status"] == "offen":
                q["antwort"] = text
                q["beantwortet"] = time.strftime("%d.%m. %H:%M")
                q["status"] = "beantwortet"
                if zugestellt_fn(q, text):
                    q["status"] = "zugestellt"
                tmp = PFAD.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
                os.replace(tmp, PFAD)
                return q
        return None
    finally:
        sperre.close()


def zurueck_auf_beantwortet(frage_id: int) -> None:
    """Zustellung scheiterte: Frage wieder auf „beantwortet“, damit das Brain sie weitergibt."""
    sperre = open(str(PFAD) + ".lock", "w")
    fcntl.flock(sperre, fcntl.LOCK_EX)
    try:
        d = _laden()
        for q in d["fragen"]:
            if q["id"] == frage_id and q["status"] == "zugestellt":
                q["status"] = "beantwortet"
        tmp = PFAD.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        os.replace(tmp, PFAD)
    finally:
        sperre.close()
