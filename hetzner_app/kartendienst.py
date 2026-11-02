"""Schmaler Dienstzugang für Kaira zu den Karten (Roli 02.11.2026 „22. bis 24. Ja“, Regel
`Kaira-Assistent/RECHTE-KARTEN.md`).

Eigener kleiner Dienst nur auf 127.0.0.1:8831, nicht hinter Caddy. Jeder Aufruf braucht den
Schlüssel aus ~/.kaira-karten-schluessel (Rechte 600, Zeile KARTEN_SCHLUESSEL=...), gesendet als
`Authorization: Bearer ...`. Was Kaira darf, steht in der Regel; das Ja von Roli auf den
vorgelesenen Wortlaut holt Kaira selbst ein, dieser Dienst erzwingt nur die harten Grenzen:

Lesen (immer): GET /karten (Zustand, Kontext, letzte Antwort als eine Zeile), GET /protokoll.
Mit Roli-Ja: POST /senden, /starten, /schlafen, /uebergabe. Zusammen höchstens 10 je Stunde.
Nie: Zugangsdaten, Löschen, Rechte ändern, Dienste neu starten, kein Verlauf im Ganzen.
Jede schreibende Aktion steht mit Zeit, Ziel und Wortlaut in ~/logs/kaira-karten.log.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import time
from pathlib import Path

import uvicorn
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

from . import kartenwechsel, mitschrift, state, tmux, tts, verbrauch

SCHLUESSELDATEI = Path.home() / ".kaira-karten-schluessel"
PROTOKOLL = Path.home() / "logs" / "kaira-karten.log"
PORT = 8831
BREMSE_JE_STUNDE = 10
MAX_TEXT = 2000
MAX_SITZUNGEN = int(os.environ.get("HETZNER_APP_MAX_SITZUNGEN", "10"))
PROJEKTE = Path.home() / "projekte"
VORSPANN = "[Kaira im Auftrag von Roli, von ihm bestätigt] "

app = FastAPI(title="Kartendienst für Kaira", docs_url=None, redoc_url=None, openapi_url=None)


def _schluessel() -> str:
    try:
        for zeile in SCHLUESSELDATEI.read_text(encoding="utf-8").splitlines():
            if zeile.startswith("KARTEN_SCHLUESSEL="):
                return zeile.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def pruefen(authorization: str = Header(default="")) -> None:
    echt = _schluessel()
    gegeben = authorization[7:] if authorization.lower().startswith("bearer ") else ""
    if not echt or not hmac.compare_digest(gegeben.encode(), echt.encode()):
        raise HTTPException(401, "Kein Zugang.")


def _protokoll(aktion: str, ziel: str, wortlaut: str, ergebnis: str) -> None:
    PROTOKOLL.parent.mkdir(exist_ok=True)
    zeile = {"zeit": time.strftime("%Y-%m-%d %H:%M:%S"), "aktion": aktion, "ziel": ziel,
             "wortlaut": wortlaut[:MAX_TEXT], "ergebnis": ergebnis}
    with PROTOKOLL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(zeile, ensure_ascii=False) + "\n")
    try:
        PROTOKOLL.chmod(0o600)
    except OSError:
        pass


def _eintraege() -> list[dict]:
    try:
        return [json.loads(z) for z in PROTOKOLL.read_text(encoding="utf-8").splitlines() if z.strip()]
    except (OSError, ValueError):
        return []


def _bremse() -> None:
    """Höchstens 10 schreibende Aktionen in der letzten Stunde (gescheiterte zählen mit)."""
    grenze = time.time() - 3600
    n = 0
    for e in _eintraege():
        try:
            if time.mktime(time.strptime(e["zeit"], "%Y-%m-%d %H:%M:%S")) >= grenze and e.get("aktion") != "abgelehnt":
                n += 1
        except (KeyError, ValueError):
            continue
    if n >= BREMSE_JE_STUNDE:
        raise HTTPException(429, f"Bremse: schon {n} Aktionen in der letzten Stunde, höchstens {BREMSE_JE_STUNDE}.")


def _karte(name: str) -> tmux.TmuxSession:
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Karte läuft nicht (oder gibt es nicht).")
    if not treffer[0].eigen:
        raise HTTPException(403, "Diese Sitzung gehört nicht der App, sie bleibt.")
    return treffer[0]


def _eine_zeile(text: str) -> str:
    gesprochen = tts.fuer_stimme(text) or ""
    for zeile in gesprochen.splitlines():
        if zeile.strip():
            z = zeile.strip()
            return z if len(z) <= 240 else z[:237] + "..."
    return ""


def _letzte_antwort(cwd: str, kennung: str) -> str:
    if not kennung:
        return ""
    try:
        for block in reversed(mitschrift.lesen(cwd, 8, datei=kennung)):
            if block.get("typ") == "claude" and (block.get("text") or "").strip():
                return _eine_zeile(block["text"])
    except Exception:  # noqa: BLE001
        return ""
    return ""


@app.get("/karten", dependencies=[Depends(pruefen)])
def karten() -> dict:
    """Nur lesen: Name, Zustand, Kontextfüllung, letzte Antwort als eine Zeile. Nie der Verlauf."""
    out = []
    for s in state.overview():
        if s.get("archiviert") or not s.get("eigen"):
            continue
        k = verbrauch.kontext(s["cwd"]) or {}
        out.append({
            "name": s["name"], "zustand": s["state"], "ordner": Path(s["cwd"]).name,
            "kontext_token": k.get("benutzt"),
            "letzte_antwort": _letzte_antwort(s["cwd"], state.get(s["name"]).mitschrift),
        })
    return {"karten": out}


@app.get("/protokoll", dependencies=[Depends(pruefen)])
def protokoll(n: int = 20) -> dict:
    return {"eintraege": _eintraege()[-max(1, min(n, 100)):]}


class Senden(BaseModel):
    karte: str
    text: str


@app.post("/senden", dependencies=[Depends(pruefen)])
def senden(b: Senden) -> dict:
    text = b.text.strip()
    if not text or len(text) > MAX_TEXT:
        raise HTTPException(400, f"Text leer oder länger als {MAX_TEXT} Zeichen.")
    _bremse()
    s = _karte(b.karte)
    if state.detect(b.karte) == state.RUNNING:
        _protokoll("abgelehnt", b.karte, text, "Karte arbeitet gerade")
        raise HTTPException(409, "Die Karte arbeitet gerade, bitte später.")
    if tmux.dialog_zustand(b.karte) != "frei":
        _protokoll("abgelehnt", b.karte, text, "offener Dialog")
        raise HTTPException(409, "In der Karte ist gerade ein Dialog offen.")
    tmux.send_text(b.karte, VORSPANN + text)
    time.sleep(0.5)
    tmux.send_key(b.karte, "Enter")
    _protokoll("senden", s.name, text, "ok")
    return {"ok": True}


class Karte(BaseModel):
    karte: str


@app.post("/uebergabe", dependencies=[Depends(pruefen)])
def uebergabe(b: Karte) -> dict:
    _bremse()
    s = _karte(b.karte)
    if state.detect(b.karte) == state.RUNNING or tmux.dialog_zustand(b.karte) != "frei":
        _protokoll("abgelehnt", b.karte, "Übergabe", "Karte arbeitet oder Dialog offen")
        raise HTTPException(409, "Die Karte arbeitet gerade oder hat einen Dialog offen.")
    tmux.send_text(b.karte, VORSPANN + kartenwechsel.AUFTRAG)
    time.sleep(0.5)
    tmux.send_key(b.karte, "Enter")
    _protokoll("uebergabe", s.name, "Auftrag zur Übergabe", "ok")
    return {"ok": True}


@app.post("/schlafen", dependencies=[Depends(pruefen)])
def schlafen(b: Karte) -> dict:
    _bremse()
    s = _karte(b.karte)
    if state.detect(b.karte) == state.RUNNING:
        _protokoll("abgelehnt", b.karte, "schlafen", "Karte arbeitet gerade")
        raise HTTPException(409, "Die Karte arbeitet gerade, erst fertig arbeiten lassen.")
    kartenwechsel.alte_schlafen_legen({"name": s.name, "cwd": s.cwd})
    _protokoll("schlafen", s.name, "schlafen legen", "ok")
    return {"ok": True}


class Starten(BaseModel):
    ordner: str          # nur der Ordnername unter ~/projekte, z. B. "Hetzner-App"
    auftrag: str = ""    # optionaler erster Satz


@app.post("/starten", dependencies=[Depends(pruefen)])
def starten(b: Starten) -> dict:
    if not re.fullmatch(r"[\w][\w .-]{0,60}", b.ordner) or ".." in b.ordner:
        raise HTTPException(400, "Ungültiger Ordnername.")
    ziel = (PROJEKTE / b.ordner).resolve()
    if ziel.parent != PROJEKTE.resolve() or not ziel.is_dir():
        raise HTTPException(404, "Diesen Projektordner gibt es nicht (neue Ordner legt Kaira nicht an).")
    auftrag = b.auftrag.strip()
    if len(auftrag) > MAX_TEXT:
        raise HTTPException(400, f"Auftrag länger als {MAX_TEXT} Zeichen.")
    _bremse()
    if sum(1 for x in tmux.list_sessions() if x.eigen) >= MAX_SITZUNGEN:
        raise HTTPException(429, "Es laufen schon zu viele Karten, erst eine schlafen legen.")
    belegt = {x.name for x in tmux.list_sessions()} | state.vergebene_namen()
    name = kartenwechsel.naechster_name(ziel.name, belegt) if ziel.name in belegt else ziel.name
    kennung = tmux.create(name, str(ziel), modell="sonnet")
    state.update(name, cwd=str(ziel), modell="sonnet", mitschrift=kennung, schlaeft=False,
                 created_prompt=auftrag or None)
    if auftrag:
        if not tmux.warte_bis_bereit(name, 40):
            _protokoll("starten", name, auftrag, "gestartet, Auftrag nicht zugestellt")
            return {"ok": True, "karte": name, "auftrag_zugestellt": False}
        zustand = tmux.dialog_zustand(name)
        if zustand == "vertrauensfrage":
            tmux.vertrauensfrage_beantworten(name)
            tmux.warte_bis_bereit(name, 15)
        tmux.send_text(name, VORSPANN + auftrag)
        time.sleep(0.5)
        tmux.send_key(name, "Enter")
    _protokoll("starten", name, auftrag or "(ohne Auftrag)", "ok")
    return {"ok": True, "karte": name, "auftrag_zugestellt": bool(auftrag)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
