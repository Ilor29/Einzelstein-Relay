"""Skill-Beschreibungen in Deutsch und Englisch (V260).

Roli 22.11.2026 15:09: In der deutschen Oberfläche sollen die Skills deutsch
beschrieben sein, in der englischen englisch, mit einem Schalter zum Original,
und neu installierte Skills sollen gleich übersetzt werden („39. Ja“).

Jede Beschreibung wird genau einmal übersetzt und unter ihrem Fingerabdruck
(sha1 des Originaltexts) gemerkt. Ändert sich der Text, entsteht ein neuer
Fingerabdruck und damit eine neue Übersetzung. Das Original bleibt unberührt.

Übersetzt wird über das eigene Abo (`claude -p --model haiku`), ohne Werkzeuge,
ohne Hooks, ohne Plugins. Aufruf als eigener Prozess:
    python -m hetzner_app.uebersetzung
Der Server startet diesen Lauf selbst, wenn die Bibliothek Lücken hat; dazu
kommt ein nächtlicher Lauf. Eine Sperrdatei verhindert zwei Läufe zugleich.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
SPEICHER = HOME / ".hetzner-app" / "bibliothek-sprachen.json"
SPERRE = HOME / ".hetzner-app" / "bibliothek-sprachen.sperre"
PROTOKOLL = HOME / "logs" / "bibliothek-uebersetzung.log"
JE_LAUF = 20          # Beschreibungen je Modellaufruf
HOECHSTENS = 40       # Aufrufe je Lauf (Schutz vor Endlosschleife)


def fingerabdruck(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def lesen() -> dict:
    try:
        daten = json.loads(SPEICHER.read_text(encoding="utf-8"))
        return daten if isinstance(daten, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _schreiben(daten: dict) -> None:
    SPEICHER.parent.mkdir(parents=True, exist_ok=True)
    tmp = SPEICHER.with_suffix(".tmp")
    tmp.write_text(json.dumps(daten, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(SPEICHER)


VERSUCHE = 3          # V261: danach gibt ein Text auf, bis er sich ändert


def fehlende(beschreibungen: list[str]) -> list[str]:
    da = lesen()
    fehl = da.get("_fehl") or {}
    return [b for b in dict.fromkeys(beschreibungen)
            if b.strip() and fingerabdruck(b) not in da and fehl.get(fingerabdruck(b), 0) < VERSUCHE]


def laeuft() -> bool:
    """Hält gerade ein anderer Prozess die Sperre?"""
    SPERRE.parent.mkdir(parents=True, exist_ok=True)
    with open(SPERRE, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
    return False


_zuletzt_gestartet = 0.0


def im_hintergrund_starten() -> bool:
    """Vom Server aus: Lauf als eigenen Prozess anstoßen, höchstens alle 10 Minuten."""
    global _zuletzt_gestartet
    if time.time() - _zuletzt_gestartet < 600 or laeuft():
        return False
    _zuletzt_gestartet = time.time()
    PROTOKOLL.parent.mkdir(parents=True, exist_ok=True)
    with open(PROTOKOLL, "a") as log:
        subprocess.Popen([sys.executable, "-m", "hetzner_app.uebersetzung"],
                         cwd=str(Path(__file__).resolve().parent.parent),
                         stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                         start_new_session=True)
    return True


AUFTRAG = (
    "Übersetze die Beschreibungen von Software-Skills. Du bekommst ein JSON-Objekt "
    "mit Kennungen als Schlüssel und Beschreibungen als Werte. Antworte NUR mit einem "
    "JSON-Objekt mit denselben Kennungen; jeder Wert ist ein Objekt {\"de\": …, \"en\": …} "
    "mit der Beschreibung auf Deutsch und auf Englisch. Ist das Original schon in einer "
    "der Sprachen, übernimm es dort unverändert. Deutsch: normales, verständliches "
    "Deutsch, du-Form, Fachbegriffe wie Skill, Plugin, Prompt, API bleiben stehen, "
    "Befehle, Dateinamen und Zitate in Anführungszeichen bleiben wörtlich. Nichts "
    "hinzufügen, nichts weglassen, keine Erklärung außerhalb des JSON."
)


def _modell(stueck: dict[str, str]) -> dict:
    r = subprocess.run(
        ["claude", "-p", json.dumps(stueck, ensure_ascii=False), "--model", "haiku",
         "--tools", "", "--append-system-prompt", AUFTRAG, "--no-session-persistence",
         "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
         "--settings", '{"disableAllHooks":true,"enabledPlugins":{"roli-koffer@koffer":false}}',
         "--output-format", "json"],
        capture_output=True, text=True, timeout=300, stdin=subprocess.DEVNULL, cwd="/tmp",
        env={"HOME": str(HOME), "PATH": f"{HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin",
             "CLAUDE_CODE_DISABLE_TERMINAL_TITLE": "1"})
    text = str(json.loads(r.stdout).get("result") or "").strip()
    a, b = text.find("{"), text.rfind("}")
    return json.loads(text[a:b + 1])


def uebersetzen(beschreibungen: list[str]) -> int:
    """Fehlende Beschreibungen übersetzen und speichern. Gibt die Anzahl zurück."""
    offen = fehlende(beschreibungen)
    neu = 0
    for runde in range(HOECHSTENS):
        stueck_liste = offen[runde * JE_LAUF:(runde + 1) * JE_LAUF]
        if not stueck_liste:
            break
        stueck = {fingerabdruck(b): b for b in stueck_liste}
        try:
            antwort = _modell(stueck)
        except Exception as e:   # ein kaputter Durchgang hält die anderen nicht auf
            print(time.strftime("%F %T"), "Durchgang", runde, "gescheitert:", repr(e)[:200], flush=True)
            antwort = {}
        daten = lesen()
        for k, v in antwort.items():
            if k in stueck and isinstance(v, dict) and isinstance(v.get("de"), str) and isinstance(v.get("en"), str):
                daten[k] = {"de": v["de"].strip()[:1500], "en": v["en"].strip()[:1500]}
                neu += 1
        # V261 (Roli 22.11. „42. Ja“): Was ohne Übersetzung blieb, bekommt einen
        # Fehlversuch angeschrieben; nach drei Versuchen wird es nicht mehr probiert.
        fehl = daten.setdefault("_fehl", {})
        for k in stueck:
            if k not in daten:
                fehl[k] = fehl.get(k, 0) + 1
                print(time.strftime("%F %T"), "ohne Übersetzung:", k, "Versuch", fehl[k], flush=True)
        _schreiben(daten)
        print(time.strftime("%F %T"), f"Durchgang {runde}: {neu} übersetzt", flush=True)
    return neu


def main() -> None:
    SPERRE.parent.mkdir(parents=True, exist_ok=True)
    with open(SPERRE, "a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            print("läuft schon", flush=True)
            return
        from . import bibliothek
        texte = [s["original_beschreibung"] for s in bibliothek.liste()]
        print(time.strftime("%F %T"), "Start,", len(fehlende(texte)), "fehlen", flush=True)
        print(time.strftime("%F %T"), "Ende,", uebersetzen(texte), "neu", flush=True)


if __name__ == "__main__":
    main()
