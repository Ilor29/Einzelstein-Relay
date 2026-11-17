"""Übergabe kurz vor Cache-Ablauf (Roli 17.11.2026 13:26: „Cache hat einen Timer, und 2 Minuten bevor
die Zeit abläuft wird eine Übergabe geschrieben, egal wie hoch oder niedrig die Token sind.“
Plan bestätigt 13:49 „185. Deine Empfehlung“, „186. Deine Empfehlung“).

Eine Schleife im Server (`waechter`) prüft alle 30 Sekunden jede eigene Karte. Hat sie laut Cache-Uhr
(`rest_s` aus verbrauch.py) nur noch höchstens 120 Sekunden, ist ruhig, ohne Dialog, mit leerer
Eingabezeile, und liegt keine UEBERGABE.md vor, die jünger ist als Rolis letzte Nachricht, tippt der
Server den Auftrag in die Karte. Der Text beginnt mit „Automatischer Auftrag“, damit der Koffer ihn nicht
als Nachricht von Roli mitschreibt.

Schleifenschutz: (1) UEBERGABE.md jünger als Rolis letzte Nachricht, dann Ruhe; (2) je Karte höchstens
ein Auftrag je Cache-Zeit (Stand-Datei, überlebt Neustarts); (3) kein Auftrag, wenn der Übergabe-Wächter
oder der Kartenwechsel eben selbst einen geschickt hat. Karten, die sich einen Ordner teilen, bleiben
außen vor. Ausschalten: Datei ~/.hetzner-app/uebergabe-cache.aus anlegen.
"""
from __future__ import annotations

import asyncio
import collections
import json
import os
import time
from pathlib import Path

from . import state, tmux, verbrauch

FENSTER_S = 120         # so kurz vor Ablauf des Caches wird der Auftrag geschickt
TAKT = 30               # so oft schaut die Schleife nach
FREMD_AUFTRAG_S = 1800  # hat ein anderer Wächter so kurz vorher geschickt, nicht doppelt
SUCH_BYTES = 16 * 1024 * 1024   # so weit hinten im Verlauf wird Rolis letzte Nachricht gesucht

STAND = Path.home() / ".hetzner-app" / "uebergabe-cache.json"
AUS = Path.home() / ".hetzner-app" / "uebergabe-cache.aus"
WAECHTER = Path.home() / ".hetzner-app" / "uebergabe-waechter.json"
WECHSEL = Path.home() / ".hetzner-app" / "kartenwechsel.json"
LOG = Path.home() / "logs" / "uebergabe-cache.log"

# Muss mit „Automatischer Auftrag“ beginnen (Koffer-Filter).
AUFTRAG = (
    "Automatischer Auftrag: Der Cache läuft in zwei Minuten ab. Schreibe jetzt die Übergabe "
    "(UEBERGABE.md im Projektordner, Stand, offen, nächster Schritt, Beschlüsse) und nenne Roli "
    "kurz den Satz Übergabe lesen."
)

# Dieselben Filter wie im Koffer: was keine Nachricht von Roli ist.
AUTOMATIK = ("This session is being continued", "<task-notification", "Automatischer Auftrag",
             "Another Claude session", "<cross-session", "<local-command", "<command-name",
             "Caveat:", "[Request interrupted", "[SYSTEM NOTIFICATION", "<system-reminder")


def log(text: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(time.strftime("%d.%m. %H:%M:%S ") + text + "\n")


def _json(pfad: Path) -> dict:
    try:
        d = json.loads(pfad.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _texte(eintrag: dict) -> list[str]:
    c = (eintrag.get("message") or {}).get("content")
    if isinstance(c, str):
        return [c]
    return [b.get("text", "") for b in (c or []) if isinstance(b, dict) and b.get("type") == "text"]


def roli_zeit(datei: Path | None) -> float:
    """Zeitpunkt von Rolis letzter echter Nachricht in der Mitschrift; 0, wenn keine gefunden wird
    (dann gilt sie als uralt, damit die Karte nicht stündlich eine zweite Übergabe schreibt)."""
    if datei is None:
        return 0.0
    try:
        with open(datei, "rb") as f:
            f.seek(0, os.SEEK_END)
            groesse = f.tell()
            f.seek(max(0, groesse - SUCH_BYTES))
            rest = f.read().decode("utf-8", "replace")
    except OSError:
        return 0.0
    for zeile in reversed(rest.splitlines()):
        if '"user"' not in zeile:
            continue
        try:
            e = json.loads(zeile)
        except ValueError:
            continue
        if (e.get("type") != "user" or e.get("isMeta") or e.get("isSidechain")
                or e.get("toolUseResult") is not None):
            continue
        for t in _texte(e):
            t = t.strip()
            if t and not t.startswith(AUTOMATIK):
                return verbrauch._zeitpunkt(e.get("timestamp")) or 0.0
    return 0.0


def eingabe_leer(name: str) -> bool:
    """Steht in der Eingabezeile der Karte kein angefangener Text? (Zeile „❯“ bis zum nächsten Strich.)"""
    try:
        zeilen = tmux.capture(name, lines=None).rstrip().splitlines()[-12:]
    except tmux.TmuxError:
        return False
    for i in range(len(zeilen) - 1, -1, -1):
        if zeilen[i].lstrip().startswith("❯"):
            if zeilen[i].lstrip()[1:].strip():
                return False
            for z in zeilen[i + 1:]:
                if z.startswith("─"):
                    return True
                if z.strip():
                    return False
            return True
    return False   # keine Eingabezeile erkennbar: lieber nichts tippen


def _frisch_gesendet(name: str, jetzt: float) -> bool:
    w = _json(WAECHTER).get(name) or {}
    k = _json(WECHSEL).get(name) or {}
    letzte = max(w.get("zeit", 0), k.get("auftrag", 0))
    return jetzt - letzte < FREMD_AUFTRAG_S


def pruefen(probe: bool = False, kontext_fn=None, jetzt: float | None = None) -> list[str]:
    """Ein Durchlauf. Gibt die Namen der Karten zurück, denen ein Auftrag geschickt wurde
    (bei probe: geschickt würde). `kontext_fn(cwd, mitschrift)` ersetzt in Proben die Cache-Auskunft."""
    if AUS.exists():
        return []
    kontext = kontext_fn or verbrauch.kontext
    jetzt = jetzt if jetzt is not None else time.time()
    gemerkt = _json(STAND)
    karten = [s for s in state.overview() if not s.get("archiviert") and s.get("eigen")]
    je_ordner = collections.Counter(s["cwd"] for s in karten if s["state"] != "sleeping")
    gesendet: list[str] = []
    for s in karten:
        name = s["name"]
        if s["state"] not in ("idle", "waiting") or je_ordner[s["cwd"]] > 1:
            continue
        meta = state.get(name)
        k = kontext(s["cwd"], meta.mitschrift) or {}
        c = k.get("cache")
        if not c or not (0 < c.get("rest_s", 0) <= FENSTER_S):
            continue
        if jetzt - (gemerkt.get(name) or {}).get("zeit", 0) < c.get("ttl_s", 3600):
            continue
        if _frisch_gesendet(name, jetzt):
            continue
        datei = verbrauch._mitschrift_datei(s["cwd"], meta.mitschrift)
        try:
            uebergabe = (Path(s["cwd"]) / "UEBERGABE.md").stat().st_mtime
        except OSError:
            uebergabe = 0.0
        if uebergabe > roli_zeit(datei):
            continue
        if tmux.dialog_zustand(name) != "frei" or not eingabe_leer(name):
            continue
        if state.detect(name) == state.RUNNING:   # frisch nachsehen, die Übersicht kann veraltet sein
            continue
        if not probe:
            tmux.send_text(name, AUFTRAG)
            time.sleep(0.3)
            tmux.send_key(name, "Enter")
            gemerkt[name] = {"zeit": int(jetzt), "rest_s": c["rest_s"], "benutzt": k.get("benutzt", 0)}
            STAND.parent.mkdir(exist_ok=True)
            STAND.write_text(json.dumps(gemerkt, ensure_ascii=False), encoding="utf-8")
            log(f"Auftrag an {name} ({k.get('benutzt', 0)} Token, Cache noch {c['rest_s']} s)")
        gesendet.append(name)
    return gesendet


async def waechter() -> None:
    """Läuft, solange der Dienst läuft."""
    while True:
        try:
            await asyncio.to_thread(pruefen)
        except Exception as e:  # noqa: BLE001  — ein Fehler darf den Dienst nie umbringen
            try:
                log(f"Fehler: {e!r}")
            except OSError:
                pass
        await asyncio.sleep(TAKT)
