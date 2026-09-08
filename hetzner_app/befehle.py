"""Die eigenen Schnellbefehle — auf dem Server, nicht im einzelnen Handy.

Bis V160 lagen sie im Gerätespeicher des Browsers. Wer am Handy einen Befehl
anlegte und danach am Rechner arbeitete, fand dort seine Leiste leer vor
(Rolis Fund 08.09.). Also liegen sie jetzt hier: eine Datei je Server, für
alle angemeldeten Geräte dieselbe.

Bewusst KEINE Trennung nach Gerät oder Person: Diese Instanz gehört einem
Menschen, seine Geräte sollen dasselbe sehen. Das ist der ganze Zweck.
"""

from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path

DATEI = Path.home() / ".hetzner-app" / "befehle.json"

# Genug für jede vernünftige Leiste, und eine Grenze gegen versehentliches
# Vollschreiben: ein Knopf trägt einen Namen, keinen Aufsatz.
MAX_BEFEHLE = 60
MAX_LABEL = 40
MAX_TEXT = 2000

# Schreiben und Lesen laufen aus mehreren Anfragen gleichzeitig — ohne Sperre
# könnten zwei Geräte ihre Listen ineinander schreiben.
_sperre = threading.Lock()


def _sauber(roh: object) -> list[dict]:
    """Aus dem, was hereinkommt, eine Liste sauberer Befehle machen.

    Alles Unbekannte fliegt raus. Der Name landet später als textContent in
    der Seite (nie als HTML), aber eine kaputte Datei soll die Leiste gar
    nicht erst erreichen.
    """
    if not isinstance(roh, list):
        return []
    liste = []
    for eintrag in roh[:MAX_BEFEHLE]:
        if not isinstance(eintrag, dict):
            continue
        label = str(eintrag.get("label", "")).strip()[:MAX_LABEL]
        text = str(eintrag.get("text", "")).strip()[:MAX_TEXT]
        if not label or not text:
            continue
        liste.append({
            "label": label,
            "text": text,
            "leiste": bool(eintrag.get("leiste")),
        })
    return liste


def lesen() -> list[dict] | None:
    """Die gespeicherten Befehle — oder None, wenn hier noch nie etwas lag.

    Der Unterschied ist wichtig: None heißt „der Server weiß nichts", dann
    schickt das erste Gerät seine örtlichen Befehle herauf. Eine leere Liste
    dagegen heißt „bewusst alles gelöscht" und darf nicht wieder aufgefüllt
    werden.
    """
    if not DATEI.exists():
        return None
    try:
        return _sauber(json.loads(DATEI.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return None


def schreiben(roh: object) -> list[dict]:
    """Die Befehle ablegen. Zurück kommt, was wirklich gespeichert wurde."""
    liste = _sauber(roh)
    inhalt = json.dumps(liste, indent=2, ensure_ascii=False)
    with _sperre:
        DATEI.parent.mkdir(parents=True, exist_ok=True)
        # Eigene Temp-Datei je Aufruf und atomares Ersetzen — wie bei den
        # Sitzungs-Metadaten: Bei einem Absturz steht nie eine halbe Liste da.
        fd, tmp = tempfile.mkstemp(dir=DATEI.parent, prefix=DATEI.name + ".", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(inhalt)
            os.replace(tmp, DATEI)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    return liste
