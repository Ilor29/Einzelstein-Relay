"""Verbrauch — wie voll das Kontextfenster ist und wo die Plan-Limits stehen.

Zwei Fragen, zwei Quellen:

 1. Kontextfenster. Claude Code schreibt jede Unterhaltung als Mitschrift nach
    ~/.claude/projects/<ordner>/<sitzung>.jsonl, und jeder Antwort-Eintrag
    trägt eine Token-Abrechnung. Die letzte davon IST der aktuelle Füllstand:
    alles, was beim jüngsten Aufruf als Eingabe ins Modell ging. Wir lesen nur
    das Datei-Ende — die Mitschriften werden viele Megabyte groß.

 2. Plan-Limits (5-Stunden-Fenster, Wochen-Limits). Die kennt nur Anthropic.
    Claude Code fragt sie über den Anmelde-Endpunkt ab; wir stellen dieselbe
    Frage mit derselben Anmeldung (~/.claude/.credentials.json). Der Weg ist
    nicht offiziell dokumentiert — wenn er eines Tages bricht, zeigt die App
    schlicht keine Limits mehr an, mehr passiert nicht. Darum ist hier alles
    doppelt abgesichert: Jeder Fehler heißt None, nie Absturz.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

# --- Kontextfenster -----------------------------------------------------------

# Die Obergrenzen der Modelle (Stand 08/2026): Fable, Opus und Sonnet haben
# 1 Million Token Kontext, nur Haiku 200.000. Neue unbekannte Modelle werden
# vorsichtshalber wie Haiku behandelt — lieber zu früh "voll" zeigen als zu spät.
_MILLION = 1_000_000
_KLEIN = 200_000


def _limit_fuer(modell: str) -> int:
    m = modell.lower()
    if "fable" in m or "opus" in m or "sonnet" in m or "mythos" in m:
        return _MILLION
    return _KLEIN


def _projekt_ordner(cwd: str) -> Path:
    # Claude Code macht aus dem Projektpfad einen Ordnernamen, indem ALLES
    # außer Buchstaben und Ziffern zu "-" wird ("Präsi TOOL" → "Pr-si-TOOL").
    kuerzel = re.sub(r"[^A-Za-z0-9]", "-", cwd)
    return Path.home() / ".claude" / "projects" / kuerzel


# Mitschriften nicht bei jedem Aufruf neu lesen: Die Antwort ändert sich nur,
# wenn die Datei sich ändert. Schlüssel ist (Pfad, Größe, Änderungszeit).
_kontext_cache: dict[str, tuple[tuple, dict | None]] = {}


def kontext(cwd: str) -> dict | None:
    """Der Kontext-Füllstand der jüngsten Unterhaltung in diesem Ordner.

    Liefert {"benutzt": Token, "limit": Token, "prozent": 0–100, "modell": …}
    oder None, wenn es (noch) nichts zu wissen gibt.
    """
    try:
        ordner = _projekt_ordner(cwd)
        dateien = [p for p in ordner.glob("*.jsonl")]
        if not dateien:
            return None
        # Die zuletzt beschriebene Mitschrift gehört zur laufenden Sitzung.
        datei = max(dateien, key=lambda p: p.stat().st_mtime)
        st = datei.stat()
        schluessel = (str(datei), st.st_size, st.st_mtime_ns)
        alt = _kontext_cache.get(cwd)
        if alt and alt[0] == schluessel:
            return alt[1]
        wert = _kontext_lesen(datei)
        _kontext_cache[cwd] = (schluessel, wert)
        return wert
    except OSError:
        return None


def _kontext_lesen(datei: Path, happen: int = 262_144) -> dict | None:
    """Die jüngste Token-Abrechnung vom Ende der Mitschrift."""
    with open(datei, "rb") as f:
        f.seek(0, os.SEEK_END)
        groesse = f.tell()
        f.seek(max(0, groesse - happen))
        rest = f.read().decode("utf-8", "replace")

    for zeile in reversed(rest.splitlines()):
        if '"usage"' not in zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            continue        # die erste Zeile des Happens ist oft angeschnitten
        # Unteragenten führen eigene Unterhaltungen mit eigenem, kleinerem
        # Kontext — ihr Füllstand ist nicht der der Sitzung.
        if eintrag.get("isSidechain") or eintrag.get("type") != "assistant":
            continue
        usage = eintrag.get("message", {}).get("usage") or {}
        benutzt = (
            (usage.get("input_tokens") or 0)
            + (usage.get("cache_read_input_tokens") or 0)
            + (usage.get("cache_creation_input_tokens") or 0)
        )
        if benutzt <= 0:
            continue
        modell = eintrag.get("message", {}).get("model") or ""
        limit = _limit_fuer(modell)
        return {
            "benutzt": benutzt,
            "limit": limit,
            "prozent": min(100, round(benutzt * 100 / limit)),
            "modell": modell,
        }
    return None


# --- Plan-Limits --------------------------------------------------------------

_ANMELDUNG = Path.home() / ".claude" / ".credentials.json"
_ENDPUNKT = "https://api.anthropic.com/api/oauth/usage"

# Die Antwort ändert sich im Minutentakt, nicht im Sekundentakt — und jeder
# Aufruf kostet eine echte Netzanfrage. Also kurz merken.
_LIMITS_GILT = 120          # Sekunden
_limits_cache: tuple[float, list | None] = (0.0, None)

# Menschliche Namen für die technischen Limit-Arten.
_NAMEN = {
    "session": "5-Stunden-Limit",
    "weekly_all": "Woche · alle Modelle",
}


def limits() -> list | None:
    """Die Plan-Limits (Prozent + Zurücksetzungszeit) — oder None, wenn der
    Weg gerade nicht funktioniert (kein Login, Netz weg, Endpunkt geändert)."""
    global _limits_cache
    stand, wert = _limits_cache
    if time.time() - stand < _LIMITS_GILT:
        return wert
    wert = _limits_holen()
    _limits_cache = (time.time(), wert)
    return wert


def _limits_holen() -> list | None:
    try:
        anmeldung = json.loads(_ANMELDUNG.read_text())
        token = anmeldung["claudeAiOauth"]["accessToken"]
    except (OSError, KeyError, ValueError):
        return None

    anfrage = urllib.request.Request(
        _ENDPUNKT,
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
        },
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=6) as antwort:
            daten = json.load(antwort)
    except (urllib.error.URLError, ValueError, OSError):
        return None

    ergebnis = []
    for limit in daten.get("limits") or []:
        art = limit.get("kind") or ""
        name = _NAMEN.get(art)
        if name is None:
            # Modell-gebundene Wochen-Limits tragen ihren Modellnamen mit.
            scope = ((limit.get("scope") or {}).get("model") or {})
            modell = scope.get("display_name")
            if art == "weekly_scoped" and modell:
                name = f"Woche · {modell}"
            else:
                continue    # Unbekanntes lieber weglassen als raten
        ergebnis.append({
            "name": name,
            "prozent": limit.get("percent") or 0,
            "reset": limit.get("resets_at"),
        })
    return ergebnis or None
