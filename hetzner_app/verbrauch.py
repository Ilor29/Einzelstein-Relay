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


def _mitschrift_datei(cwd: str, mitschrift: str = "") -> Path | None:
    """Die Mitschrift-Datei, aus der gelesen wird.

    Kennt die Karte ihre eigene Mitschrift (state.Meta.mitschrift), gilt die.
    Sonst, oder wenn die Datei fehlt, die zuletzt beschriebene des Ordners:
    das war bis V224 immer so und stimmt, solange im Ordner nur eine Karte
    arbeitet. Bei zwei wachen Karten im selben Ordner zeigte sonst jede den
    Stand derjenigen, die zuletzt schrieb (Durchsicht 11.11.2026).
    """
    ordner = _projekt_ordner(cwd)
    if mitschrift and re.fullmatch(r"[A-Za-z0-9-]+", mitschrift):
        datei = ordner / f"{mitschrift}.jsonl"
        if datei.is_file():
            return datei
    dateien = list(ordner.glob("*.jsonl"))
    if not dateien:
        return None
    return max(dateien, key=lambda p: p.stat().st_mtime)


def kontext(cwd: str, mitschrift: str = "") -> dict | None:
    """Der Kontext-Füllstand der Unterhaltung dieser Karte.

    Liefert {"benutzt": Token, "limit": Token, "prozent": 0–100, "modell": …,
    "modell_zeit": Epoche} oder None, wenn es (noch) nichts zu wissen gibt.
    """
    try:
        datei = _mitschrift_datei(cwd, mitschrift)
        if datei is None:
            return None
        st = datei.stat()
        schluessel = (st.st_size, st.st_mtime_ns)
        alt = _kontext_cache.get(str(datei))
        if alt and alt[0] == schluessel:
            return _mit_cache_rest(alt[1])
        wert = _kontext_lesen(datei)
        if len(_kontext_cache) > 400:
            _kontext_cache.clear()
        _kontext_cache[str(datei)] = (schluessel, wert)
        return _mit_cache_rest(wert)
    except OSError:
        return None


_MODELL_KENNUNG = re.compile(r"^claude-([a-z]+)-(\d{1,2})(?:-(\d{1,2}))?(?:-\d{8})?$")


def modell_anzeige(kennung: str) -> str:
    """Aus der Modell-Kennung der Mitschrift den lesbaren Namen machen:
    "claude-fable-5-2" wird "Fable 5.2". Unbekannte Formen bleiben, wie sie sind."""
    t = _MODELL_KENNUNG.match(kennung or "")
    if not t:
        return kennung or ""
    name, gross, klein = t.groups()
    return f"{name.capitalize()} {gross}" + (f".{klein}" if klein else "")


# --- API-Gegenwert (Roli 04.11.2026, „46. Ja“) ----------------------------------
#
# Was dieselbe Sitzung über die Schnittstelle zum Listenpreis gekostet hätte.
# Das ist nicht die Abo-Rechnung, nur ein Vergleichswert. Gerechnet wird aus den
# Token-Zahlen der ganzen Mitschrift. Die Preise sind dieselben wie auf der
# Token-Seite im LEIT//PULS (leitstand/token-bauen.py, PREISE): Dollar je
# Million Token (Eingabe, Ausgabe, Cache lesen); Cache anlegen kostet 1,25-fach
# (5 Minuten) oder 2-fach (1 Stunde) der Eingabe. Unbekannte Modelle zählen
# nicht mit und werden als Anzahl gemeldet. Bei neuen Modellen hier nachtragen.
_PREISE = {
    "claude-fable-5-2": (8.0, 40.0, 0.20),
    "claude-fable-5-1": (10.0, 50.0, 0.25), "claude-fable-5": (10.0, 50.0, 1.0),
    "claude-opus-5-5": (4.0, 20.0, 0.20), "claude-opus-5": (5.0, 25.0, 0.5),
    "claude-opus-4-8": (5.0, 25.0, 0.5),
    "claude-sonnet-5-5": (2.0, 10.0, 0.10), "claude-sonnet-5": (2.0, 10.0, 0.20),
    "claude-haiku-5-5": (0.10, 0.50, 0.01), "claude-haiku-4-5-20251001": (1.0, 5.0, 0.10),
}
# Der Dollarkurs liegt als Datei bereit, wenn der LEIT//PULS ihn holt. Fehlt sie
# (zum Beispiel auf einem anderen Server), zeigt die App den Betrag in Dollar.
_KURS_DATEI = Path.home() / ".claude" / "kurs-usd-eur.json"
_gegenwert_cache: dict[str, tuple[tuple, dict | None]] = {}


def _dollar(modell: str, u: dict) -> float | None:
    preis = _PREISE.get(modell)
    if not preis:
        return None
    ein, aus, lesen = preis
    c = u.get("cache_creation") or {}
    if c:
        anlegen = ((c.get("ephemeral_5m_input_tokens") or 0) * 1.25
                   + (c.get("ephemeral_1h_input_tokens") or 0) * 2.0)
    else:
        anlegen = (u.get("cache_creation_input_tokens") or 0) * 1.25
    return ((u.get("input_tokens") or 0) * ein + anlegen * ein
            + (u.get("cache_read_input_tokens") or 0) * lesen
            + (u.get("output_tokens") or 0) * aus) / _MILLION


def _kurs() -> float | None:
    try:
        eur = json.loads(_KURS_DATEI.read_text()).get("rate")
        return eur if isinstance(eur, (int, float)) and 0.5 < eur < 1.5 else None
    except (OSError, ValueError):
        return None


def _gegenwert_lesen(datei: Path) -> dict | None:
    gesehen: set[str] = set()
    usd = 0.0
    unbekannt = 0
    zuege = 0
    with open(datei, encoding="utf-8", errors="replace") as h:
        for zeile in h:
            if '"usage"' not in zeile:
                continue
            try:
                d = json.loads(zeile)
            except ValueError:
                continue
            if d.get("type") != "assistant":
                continue
            nachricht = d.get("message") or {}
            u = nachricht.get("usage") or {}
            if not u:
                continue
            kennung = nachricht.get("id")
            if kennung:          # dieselbe Antwort steht oft mehrfach in der Mitschrift
                if kennung in gesehen:
                    continue
                gesehen.add(kennung)
            zuege += 1
            wert = _dollar(nachricht.get("model") or "", u)
            if wert is None:
                unbekannt += 1
            else:
                usd += wert
    if not zuege:
        return None
    return {"usd": usd, "zuege": zuege, "unbekannt": unbekannt}


def gegenwert(cwd: str, mitschrift: str = "") -> dict | None:
    """API-Gegenwert der Unterhaltung dieser Karte: {"usd", "eur" (oder None), "kurs", "zuege", "unbekannt"}."""
    try:
        datei = _mitschrift_datei(cwd, mitschrift)
        if datei is None:
            return None
        st = datei.stat()
        schluessel = (st.st_size, st.st_mtime_ns)
        alt = _gegenwert_cache.get(str(datei))
        if alt and alt[0] == schluessel:
            wert = alt[1]
        else:
            wert = _gegenwert_lesen(datei)
            if len(_gegenwert_cache) > 400:
                _gegenwert_cache.clear()
            _gegenwert_cache[str(datei)] = (schluessel, wert)
        if not wert:
            return None
        kurs = _kurs()
        return {**wert, "kurs": kurs, "eur": wert["usd"] * kurs if kurs else None}
    except OSError:
        return None


# --- Prompt-Cache -------------------------------------------------------------
#
# Anthropic hält den vorderen, unveränderten Teil einer Unterhaltung als
# Zwischenspeicher („Prompt-Cache") vor. Trifft ein Zug den Speicher, kosten
# diese Token nur ein Zehntel; ist er abgelaufen, wird der ganze Verlauf neu
# angelegt (1,25-fach) — bei einer großen Karte also rund das Zwölffache eines
# warmen Zuges. Jeder Zug erneuert die Lebensdauer. Wie lang sie ist, steht in
# jeder Abrechnung: cache_creation.ephemeral_1h_input_tokens (eine Stunde) oder
# …ephemeral_5m_input_tokens (fünf Minuten). Auf diesem Server ist praktisch
# alles auf eine Stunde (Zählung 10.10.2026: 114.000 Einträge mit 1 h gegen
# 46 mit 5 min). Die Anzeige wünschte sich Roli am 10.10.2026 16:40, um vor
# einem teuren Zug entweder weiterzuarbeiten, solange es warm ist, oder gleich
# eine Übergabe zu machen.
_CACHE_TTL_ANNAHME = 3600


def _zeitpunkt(iso: str | None) -> float | None:
    """ISO-Zeitstempel der Mitschrift („2026-10-10T14:47:32.775Z") als Epoche."""
    if not iso:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(iso).timestamp()
    except ValueError:
        return None


def _mit_cache_rest(wert: dict | None) -> dict | None:
    """Die Restwärme JETZT ausrechnen — der Rest ist aus der Mitschrift zwischengespeichert."""
    if not wert or not wert.get("cache"):
        return wert
    c = dict(wert["cache"])
    c["rest_s"] = max(0, int(c["warm_bis"] - time.time()))
    c["warm"] = c["rest_s"] > 0
    c["kalt_seit_s"] = 0 if c["warm"] else int(time.time() - c["warm_bis"])
    aus = dict(wert)
    aus["cache"] = c
    return aus


def _kontext_lesen(datei: Path, happen: int = 262_144) -> dict | None:
    """Die jüngste Token-Abrechnung vom Ende der Mitschrift — und dazu, wann der
    letzte Zug war und wie lange sein Prompt-Cache lebt."""
    with open(datei, "rb") as f:
        f.seek(0, os.SEEK_END)
        groesse = f.tell()
        f.seek(max(0, groesse - happen))
        rest = f.read().decode("utf-8", "replace")

    ergebnis: dict | None = None
    zuletzt: float | None = None     # jüngster Zug der Hauptunterhaltung
    ttl: int | None = None           # Lebensdauer des Caches laut Abrechnung
    gesehen = 0
    for zeile in reversed(rest.splitlines()):
        if '"timestamp"' not in zeile:
            continue
        try:
            eintrag = json.loads(zeile)
        except ValueError:
            continue        # die erste Zeile des Happens ist oft angeschnitten
        # Unteragenten führen eigene Unterhaltungen mit eigenem, kleinerem
        # Kontext und eigenem Cache — ihr Stand ist nicht der der Sitzung.
        if eintrag.get("isSidechain") or eintrag.get("type") not in ("user", "assistant"):
            continue
        # Der jüngste Eintrag, egal ob Frage oder Antwort: Auf jede Frage (auch
        # ein Werkzeug-Ergebnis) folgt sofort ein Zug, der den Cache erneuert.
        if zuletzt is None:
            zuletzt = _zeitpunkt(eintrag.get("timestamp"))
        if eintrag.get("type") != "assistant":
            continue
        usage = eintrag.get("message", {}).get("usage") or {}
        if ergebnis is None:
            benutzt = (
                (usage.get("input_tokens") or 0)
                + (usage.get("cache_read_input_tokens") or 0)
                + (usage.get("cache_creation_input_tokens") or 0)
            )
            if benutzt > 0:
                modell = eintrag.get("message", {}).get("model") or ""
                limit = _limit_fuer(modell)
                ergebnis = {
                    "benutzt": benutzt,
                    "limit": limit,
                    "prozent": min(100, round(benutzt * 100 / limit)),
                    "modell": modell,
                    # Wann diese Antwort kam: Daran entscheidet die Liste, ob
                    # ein Modellwechsel jünger ist als die letzte Antwort.
                    "modell_zeit": _zeitpunkt(eintrag.get("timestamp")) or 0,
                }
        if ttl is None:
            anlage = usage.get("cache_creation") or {}
            if (anlage.get("ephemeral_1h_input_tokens") or 0) > 0:
                ttl = 3600
            elif (anlage.get("ephemeral_5m_input_tokens") or 0) > 0:
                ttl = 300
        gesehen += 1
        # Reine Lese-Züge nennen keine Lebensdauer; ein paar Züge zurückschauen
        # reicht, danach gilt die Annahme (eine Stunde, siehe oben).
        if ergebnis is not None and (ttl is not None or gesehen >= 40):
            break
    if ergebnis is None:
        return None
    if zuletzt is not None:
        ergebnis["cache"] = {
            "ttl_s": ttl if ttl is not None else _CACHE_TTL_ANNAHME,
            "angenommen": ttl is None,
            "zuletzt": zuletzt,
            "warm_bis": zuletzt + (ttl if ttl is not None else _CACHE_TTL_ANNAHME),
        }
    return ergebnis


# --- Verlauf --------------------------------------------------------------

# Ein Datenpunkt je archivierter Karte: Modell und Token-Endstand. Reine
# Anhänge-Datei (JSON Lines), damit sich Opus 5 gegen Opus 5.5 & Co. später
# wirklich vergleichen lässt — ohne das wäre jeder frühere Beschluss dazu
# hinfällig, sobald die App neu startet (Rolis Ärger 23.09.2026).
_VERLAUF_DATEI = Path.home() / ".hetzner-app" / "verbrauch-verlauf.jsonl"


def protokolliere(karte: str, cwd: str, mitschrift: str = "") -> None:
    """Einen Datenpunkt für den Modell-Vergleich anhängen.

    Aufgerufen beim Archivieren einer Karte — dem Augenblick, in dem ihr
    Kontext-Verbrauch feststeht. Ohne bekannten Verbrauch passiert nichts.
    """
    wert = kontext(cwd, mitschrift)
    if wert is None:
        return
    zeile = json.dumps({
        "zeit": int(time.time()),
        "karte": karte,
        "modell": wert["modell"],
        "benutzt": wert["benutzt"],
        "limit": wert["limit"],
    }, ensure_ascii=False)
    try:
        _VERLAUF_DATEI.parent.mkdir(parents=True, exist_ok=True)
        with open(_VERLAUF_DATEI, "a") as f:
            f.write(zeile + "\n")
    except OSError:
        pass    # Verlauf ist ein Bonus — darf das Archivieren nie verhindern.


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
