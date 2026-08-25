"""Der Dienst, der auf dem Hetzner läuft.

Er tut drei Dinge:
  1. Sitzungen verwalten (auflisten, starten, beenden, anheften)
  2. Ein Terminal ans Handy durchreichen (über WebSocket)
  3. Text vorlesen (über Piper)
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import os
import re
import secrets
import shutil
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from urllib.parse import urlparse

from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, Query, Request, UploadFile,
    WebSocket, WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from . import bibliothek, geraete, melden, mitschrift, routinen, speicher, state, tmux, tts, verbrauch, verlauf

WEB_DIR = Path(__file__).parent.parent / "web"

COOKIE = "hetzner_app_anmeldung"


def _csp_bauen() -> str | None:
    """Die Content-Security-Policy — zweites Netz gegen XSS.

    Der Kniff: Die App hat genau EIN Inline-Skript (die Notbremse in
    index.html). Dessen Hash berechnen wir hier beim Start AUS DER DATEI, statt
    ihn von Hand einzutragen — so bricht die CSP nie, auch wenn die Notbremse
    mal geändert wird. Alles andere lädt die App von der eigenen Herkunft; die
    großzügigen Stellen (img/media data:/blob:) sind ungefährlich (kein fremder
    Host). Klappt das Berechnen nicht, setzen wir LIEBER GAR KEINE CSP als eine,
    die die App lahmlegt — das war schon immer die Sorge an dieser Stelle.
    """
    try:
        html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
        treffer = re.search(r"<script>(.*?)</script>", html, re.S)
        roh = hashlib.sha256(treffer.group(1).encode("utf-8")).digest()
        hash_ = base64.b64encode(roh).decode()
    except Exception:
        return None
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' 'sha256-{hash_}'",
        "style-src 'self'",
        "img-src 'self' data: blob:",
        "media-src 'self' blob:",
        "font-src 'self'",
        "connect-src 'self'",          # deckt auch same-origin WebSocket (wss)
        "worker-src 'self'",
        "manifest-src 'self'",
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
    ])


CSP = _csp_bauen()

app = FastAPI(title="Hetzner-App")


@app.middleware("http")
async def sicherheits_header(request: Request, call_next):
    """Ein paar schützende Kopfzeilen auf jede Antwort — inklusive der CSP.

    Die Content-Security-Policy ist das zweite Netz gegen XSS (das erste ist die
    textContent-Disziplin). Sie wird beim Start aus der Datei gebaut (der Hash
    des einen Inline-Skripts inklusive, siehe _csp_bauen) und im Browser-Prüfer
    getestet. Schlägt das Bauen fehl, bleibt sie weg — lieber keine CSP als eine,
    die die App lahmlegt.
    """
    # Deckel auf die Anfragengröße, BEVOR der Körper in den Speicher gelesen
    # wird. Die größte legitime Anfrage ist ein Dokument-Upload (30 MB) —
    # 35 MB lassen dafür Luft. Ohne den Deckel könnte ein angemeldetes Gerät
    # mit einem einzigen Riesen-Paket die kleine Maschine in den Speichertod
    # schicken.
    laenge = request.headers.get("content-length")
    if laenge and laenge.isdigit() and int(laenge) > 35 * 1024 * 1024:
        return JSONResponse({"detail": "Die Anfrage ist zu groß."}, status_code=413)

    antwort = await call_next(request)
    antwort.headers.setdefault("X-Content-Type-Options", "nosniff")
    antwort.headers.setdefault("Referrer-Policy", "same-origin")
    antwort.headers.setdefault("X-Frame-Options", "DENY")
    if CSP:
        antwort.headers.setdefault("Content-Security-Policy", CSP)
    return antwort


# Anhänge — Fotos und Dokumente — sind Durchgangsware: einmal an Claude gereicht,
# liegen sie nur noch als Altlast im Projekt. Diese Ordner räumen wir darum von
# selbst; sie stehen bewusst außerhalb von Git (siehe die .gitignore beim Upload).
ANHANG_ORDNER = (".hetzner-bilder", ".hetzner-dateien")

# Wie lange ein Anhang liegen bleiben darf. Ein paar Tage, damit man einen
# Screenshot von gestern noch nachreichen oder ansehen kann — aber nicht ewig.
ANHANG_HALTBAR_TAGE = 3

# Backstop gegen den Speichertod: höchstens so viele gleichzeitig LEBENDE
# eigene Sitzungen. Jede Claude-Sitzung hält 200–500 MB; ohne Deckel könnte ein
# Gerät mit ein paar Fingertipps den kleinen Server in den OOM-Kill treiben
# (siehe 17.07.). Schlafende zählen nicht — sie haben kein Terminal. Auf einem
# größeren Server per Umgebungsvariable anhebbar.
MAX_SITZUNGEN = int(os.environ.get("HETZNER_APP_MAX_SITZUNGEN", "10"))

# Das Ton-Tagebuch war ein Fehlersuch-Werkzeug fürs Vorlesen (Hosentaschen-
# Abbruch, V100). In einer weitergegebenen Fassung wäre es ungefragte
# Nutzungs-Telemetrie — darum standardmäßig AUS. Zum Debuggen einschalten mit
# HETZNER_APP_TON_TAGEBUCH=1 in der Umgebung (und dem Schalter in app.js).
TON_TAGEBUCH_AN = os.environ.get("HETZNER_APP_TON_TAGEBUCH") == "1"


def _anhang_ordner() -> set[Path]:
    """Alle Durchgangs-Ordner, die es aufzuräumen gilt.

    Aus zwei Quellen, damit keiner durchrutscht: die Projekte unter ~/projekte
    (auch die ohne laufende Sitzung) und die Arbeitsordner der lebenden
    Sitzungen (falls eine mal woanders als unter ~/projekte läuft).
    """
    ordner: set[Path] = set()
    wurzel = Path.home() / "projekte"
    if wurzel.is_dir():
        for projekt in wurzel.iterdir():
            for name in ANHANG_ORDNER:
                ordner.add(projekt / name)
    for s in tmux.list_sessions():
        for name in ANHANG_ORDNER:
            ordner.add(Path(s.cwd) / name)
    return {o for o in ordner if o.is_dir()}


def _alte_anhaenge_loeschen() -> int:
    """Löscht Anhänge, die älter sind als ANHANG_HALTBAR_TAGE. Gibt die Zahl
    der gelöschten Dateien zurück."""
    grenze = time.time() - ANHANG_HALTBAR_TAGE * 86400
    geloescht = 0
    for ordner in _anhang_ordner():
        for datei in ordner.iterdir():
            # Die .gitignore hält den Ordner aus Git heraus — die bleibt.
            if datei.name == ".gitignore" or not datei.is_file():
                continue
            try:
                if datei.stat().st_mtime < grenze:
                    datei.unlink()
                    geloescht += 1
            except OSError:
                pass          # eine störrische Datei hält das Aufräumen nicht auf
    return geloescht


async def anhaenge_aufraeumen() -> None:
    """Räumt in aller Ruhe alle paar Stunden die Durchgangs-Ordner leer.

    Aufräumen ist Nebensache — es darf die App unter keinen Umständen stören,
    darum steckt jeder Durchlauf in einem breiten Fangnetz.
    """
    while True:
        try:
            await asyncio.to_thread(_alte_anhaenge_loeschen)
        except Exception:
            pass
        await asyncio.sleep(6 * 3600)


async def piper_waechter() -> None:
    """Hält Pipers Speicher im Zaum: alle paar Minuten nachsehen und, wenn er
    zu groß geworden ist (viele geladene Stimmen), im Leerlauf frisch starten.
    Gerade auf kleinen Community-Servern wichtig (siehe tts.speicher_pruefen).
    """
    while True:
        await asyncio.sleep(300)          # alle 5 Minuten
        try:
            await asyncio.to_thread(tts.speicher_pruefen)
        except Exception:
            pass


@app.on_event("startup")
async def waechter_starten() -> None:
    """Der Wächter behält die Sitzungen im Auge und meldet sich, wenn eine
    fertig ist oder eine Rückfrage hat."""
    # Geburtsstempel für die Erst-Besucher-Kopplung — einmalig, nie überschrieben.
    geraete.erststart_merken()

    asyncio.create_task(melden.waechter())

    # Die Stimme schon mal in den Speicher holen. Sonst wartet man beim ersten
    # Vorlesen drei Sekunden auf ein Modell, das man auch vorher hätte laden
    # können.
    asyncio.create_task(asyncio.to_thread(tts.vorladen))

    # Alte Anhänge (Fotos, Dokumente) von selbst wegräumen.
    asyncio.create_task(anhaenge_aufraeumen())

    # Piper im Zaum halten, damit er den kleinen Server nicht vollsaugt.
    asyncio.create_task(piper_waechter())


# --- Zugangsschutz -----------------------------------------------------------

def require_auth(request: Request) -> None:
    marke = request.cookies.get(COOKIE, "")
    if not geraete.anmeldung_gueltig(marke):
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")
    # Wer die App aktiv benutzt, soll nicht mitten in der Arbeit rausfliegen —
    # die kurze Grundlaufzeit wird bei Nutzung stillschweigend aufgefrischt.
    geraete.anmeldung_benutzt(marke)


class Unterschrift(BaseModel):
    aufgabe: str
    unterschrift: str


# Hochzählen, sobald sich an der Oberfläche etwas ändert. Die App prüft das
# beim Start und lädt sich selbst neu, wenn sie veraltet ist — sonst läuft man
# stundenlang gegen einen Fehler an, der längst behoben ist.
VERSION = 136


@app.get("/api/version")
def version() -> dict:
    return {"version": VERSION}


@app.get("/api/aufgabe")
def aufgabe() -> dict:
    """Die Zufallsaufgabe, die das Gerät unterschreiben muss.

    Sie zu kennen nützt niemandem — unterschreiben kann sie nur, wer den
    geheimen Schlüssel hat, und der liegt im Handy.
    """
    return {"aufgabe": geraete.aufgabe_stellen()}


@app.post("/api/anmelden")
def anmelden(body: Unterschrift) -> Response:
    geraet = geraete.unterschrift_pruefen(body.aufgabe, body.unterschrift)
    if geraet is None:
        raise HTTPException(401, "Dieses Gerät ist nicht freigeschaltet.")

    antwort = JSONResponse({"ok": True, "geraet": geraet.name})
    antwort.set_cookie(
        COOKIE, geraete.anmeldung_ausstellen(geraet.name),
        httponly=True,
        samesite="strict",
        secure=True,        # nur über HTTPS — siehe Caddy-Konfiguration
        # Der Browser darf die Marke lange behalten; wie lange sie WIRKLICH gilt,
        # entscheidet allein der Server (90 Tage, bei Nutzung verlängert). So ist
        # ein abgegriffener Cookie nicht ewig gültig und bleibt widerrufbar.
        max_age=60 * 60 * 24 * 365,
    )
    return antwort


@app.post("/api/abmelden")
def abmelden(request: Request) -> Response:
    """Dieses Gerät abmelden — Marke widerrufen und Cookie löschen."""
    geraete.abmelden(request.cookies.get(COOKIE, ""))
    antwort = JSONResponse({"ok": True})
    antwort.delete_cookie(COOKIE, httponly=True, samesite="strict", secure=True)
    return antwort


class Koppeln(BaseModel):
    schluessel: str
    code: str = ""               # leer = Erst-Besucher-Kopplung (nur solange offen)
    name: str = "Handy"


@app.get("/api/kopplung/offen")
def kopplung_offen() -> dict:
    """Steht die Erst-Besucher-Tür noch offen? (bewusst nur Ja/Nein)

    Unangemeldet erreichbar, weil die Koppel-Ansicht es VOR der Anmeldung
    wissen muss. Mehr als Ja/Nein verrät der Endpunkt nicht — und ein
    Kopplungs-Versuch würde dasselbe verraten (CODE-GUARD-Bericht, 🟡).
    """
    return {"offen": geraete.erstkopplung_offen()}


@app.post("/api/koppeln")
def koppeln(body: Koppeln) -> Response:
    """Ein neues Gerät per Kopplungscode selbst freischalten — ohne Kommandozeile.

    Der Code ist ein Geheimnis: setup.sh druckt ihn beim Einrichten, oder ein
    schon freigeschaltetes Gerät erzeugt ihn (siehe /api/kopplung/neu). Stimmt
    er, wird dieses Gerät eingetragen und gleich angemeldet.

    Ausnahme ohne Code: die Erst-Besucher-Kopplung — nur solange NOCH KEIN
    Gerät eingetragen und der Server jung ist (siehe geraete.py und
    CODE-GUARD-Bericht-Erstkopplung.md). Danach öffnet die Tür weiterhin nur,
    wer das Geheimnis kennt.
    """
    # Erst den Schlüssel prüfen, DANN den Code verbrauchen: Sonst wäre der Code
    # bei einem unbrauchbaren Schlüssel schon aufgebraucht, obwohl gar nichts
    # eingetragen wurde.
    if not geraete.schluessel_ok(body.schluessel):
        raise HTTPException(400, "Der Geräteschlüssel ist unbrauchbar.")

    name = body.name.strip()[:40] or "Handy"
    if not body.code.strip():
        geraet = geraete.erstkopplung_versuchen(name, body.schluessel)
        if geraet is None:
            raise HTTPException(
                403,
                "Dieser Server gehört schon jemandem (oder das Erst-Fenster ist "
                "vorbei) — bitte mit Kopplungscode freischalten.",
            )
    else:
        if not geraete.kopplung_pruefen_und_verbrauchen(body.code):
            raise HTTPException(403, "Der Kopplungscode stimmt nicht oder ist abgelaufen.")
        geraet = geraete.erlauben(name, body.schluessel)
    antwort = JSONResponse({"ok": True, "geraet": geraet.name})
    antwort.set_cookie(
        COOKIE, geraete.anmeldung_ausstellen(geraet.name),
        httponly=True, samesite="strict", secure=True,
        max_age=60 * 60 * 24 * 365,
    )
    return antwort


@app.post("/api/kopplung/neu", dependencies=[Depends(require_auth)])
def kopplung_neu() -> dict:
    """Einen frischen Kopplungscode erzeugen — für ein WEITERES Gerät.

    Nur ein schon angemeldetes Gerät darf das. So fügt man vom Handy aus ein
    zweites Gerät (Tablet, Laptop) hinzu, ganz ohne Server-Terminal.
    """
    return {"code": geraete.kopplung_neu()}


@app.get("/api/geraete", dependencies=[Depends(require_auth)])
def geraete_liste() -> list[dict]:
    return [{"name": g.name, "hinzugefuegt": g.hinzugefuegt} for g in geraete.liste()]


@app.delete("/api/geraete/{name}", dependencies=[Depends(require_auth)])
def geraet_aussperren(name: str) -> dict:
    """Ein verlorenes Gerät aussperren — Schlüssel weg, laufende Anmeldung weg."""
    if not geraete.entfernen(name):
        raise HTTPException(404, "Dieses Gerät gibt es nicht.")
    return {"ok": True}


# --- Sitzungen ---------------------------------------------------------------

class NewSession(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9._ -]+$")
    cwd: str
    first_prompt: str = ""
    pinned: bool = False
    notify_when_done: bool = False
    # "Fragt nie": Claude führt auch Befehle ohne Rückfrage aus. Nur beim Start
    # setzbar, nicht später umschaltbar.
    ohne_rueckfragen: bool = False


class Patch(BaseModel):
    pinned: bool | None = None
    notify_when_done: bool | None = None
    # Wie die Sitzung heißen soll. Der technische Name der tmux-Sitzung bleibt,
    # wie er ist — sonst verlöre alles andere seinen Bezug. Wir merken uns nur,
    # wie sie im Handy heißen soll.
    anzeige: str | None = None
    # Ins Archiv stellen oder herausholen — nur für Karten ohne Terminal
    # (schlafend/abgestürzt) gedacht; Aufwecken löst es von selbst.
    archiviert: bool | None = None


@app.get("/api/sessions", dependencies=[Depends(require_auth)])
def list_sessions() -> list[dict]:
    return state.overview()


# Die Startausstattung für frische Projekte. Liegt im App-Repo (mitgesichert,
# und beim Verkauf Teil des Produkts): eine CLAUDE.md-Vorlage und ein
# .gitignore, damit kein Projekt mehr „blank" beginnt.
VORLAGE = Path(__file__).resolve().parent.parent / "vorlage"


def _vorlage_einrichten(ordner: Path) -> None:
    """Legt die Vorlage in ein frisches Projekt und macht es zu einem Git-Repo.

    Ohne das Git-Repo überspränge die automatische Sicherung das Projekt
    stillschweigend — genau so ist früher schon Arbeit unversioniert geblieben.
    """
    if VORLAGE.is_dir():
        for quelle in VORLAGE.iterdir():
            ziel = ordner / quelle.name
            if ziel.exists():
                continue
            if quelle.is_dir():
                shutil.copytree(quelle, ziel)
            else:
                shutil.copy(quelle, ziel)
    subprocess.run(["git", "init", "--quiet", str(ordner)], capture_output=True)


def _sicherer_sitzungsname(roh: str) -> str:
    """Ein Name, der als tmux-Sitzungsname unverändert überlebt.

    tmux schreibt '.' und ':' im Sitzungsnamen still zu '_' um — danach sucht
    die App ihre Sitzung unter dem eingegebenen Namen und findet sie nie wieder
    (genau der „geht nicht"-Fehler bei „Hetzner-App 1.1"). Also ersetzen wir die
    Zeichen selbst, damit gespeicherter Name und tmux-Name deckungsgleich sind.
    """
    name = roh.strip()
    for zeichen in ".:":
        name = name.replace(zeichen, "_")
    return name


@app.post("/api/sessions", dependencies=[Depends(require_auth)])
async def create_session(body: NewSession) -> dict:
    cwd = Path(body.cwd).expanduser()
    if not cwd.is_dir():
        # Ein Ordner, den es nicht gibt, darf ein NEUES Projekt werden — aber
        # nur direkt unter ~/projekte und ohne Punkt-Namen. Alles andere bleibt
        # ein Fehler: Die App soll keine Ordner irgendwo im System anlegen.
        wurzel = (Path.home() / "projekte").resolve()
        ziel = cwd.resolve()
        if ziel.parent != wurzel or ziel.name.startswith("."):
            raise HTTPException(400, f"Den Ordner {body.cwd} gibt es nicht.")
        ziel.mkdir()
        _vorlage_einrichten(ziel)
        cwd = ziel

    # Ab hier durchgehend den tmux-sicheren Namen benutzen — sonst laufen
    # gespeicherter Name und tmux-Sitzung auseinander.
    name = _sicherer_sitzungsname(body.name)
    if not name:
        raise HTTPException(400, "Bitte einen Namen für die Sitzung angeben.")

    # Backstop gegen den Speichertod: nicht mehr als MAX_SITZUNGEN lebende
    # eigene Sitzungen gleichzeitig. Schlafende zählen nicht.
    eigene = sum(1 for s in tmux.list_sessions() if s.eigen)
    if eigene >= MAX_SITZUNGEN:
        raise HTTPException(
            429,
            f"Es laufen schon {eigene} Sitzungen. Leg erst eine schlafen "
            "(Mond-Knopf auf der Karte), bevor du eine neue startest.",
        )

    try:
        tmux.create(name, str(cwd), ohne_rueckfragen=body.ohne_rueckfragen)
    except tmux.TmuxError as error:
        raise HTTPException(409, str(error))

    state.update(
        name,
        pinned=body.pinned,
        notify_when_done=body.notify_when_done,
        created_prompt=body.first_prompt,
        # Fürs spätere Schlafen/Aufwecken: den Ordner und den Startmodus
        # merken — tmux weiß beides nicht mehr, sobald die Sitzung beendet ist.
        cwd=str(cwd),
        ohne_rueckfragen=body.ohne_rueckfragen,
        schlaeft=False,
        # Trägt eine alte (schlafende/abgestürzte) Karte denselben Namen,
        # würde die neue Sitzung sonst deren Gesprächs-Bindung erben und
        # dauerhaft den fremden Verlauf zeigen (Fund der Code-Durchsicht
        # 20.08.). Frische Sitzung, frische Erkennung.
        mitschrift="",
    )

    if body.first_prompt:
        # Der erste Auftrag darf nicht auf die Antwort warten lassen. Claude
        # Code braucht ein paar Sekunden, bis es Eingaben annimmt — solange
        # dürfen wir das Handy nicht hängen lassen. Also: Sitzung sofort
        # melden, Auftrag im Hintergrund nachschieben.
        asyncio.create_task(_ersten_auftrag_schicken(name, body.first_prompt))

    return {"ok": True, "name": name}


async def _ersten_auftrag_schicken(name: str, prompt: str) -> None:
    """Wartet, bis Claude Code zuhört, und tippt dann den Auftrag."""
    bereit = await asyncio.to_thread(tmux.warte_bis_bereit, name, 40)
    if not bereit:
        return
    # Auch beim allerersten Auftrag kann schon ein Dialog über der Eingabe
    # liegen (Einrichtungsfragen beim Start). Wegdrücken, wenn er es selbst
    # anbietet — sonst tippt der Auftrag ins Leere.
    if await asyncio.to_thread(tmux.dialog_zustand, name) == "abbrechbar":
        tmux.send_key(name, "Escape")
        await asyncio.sleep(0.8)
    tmux.send_text(name, prompt)
    # Kurz Luft lassen: Text und Enter im selben Atemzug verschluckt Claude
    # Code gelegentlich.
    await asyncio.sleep(0.5)
    tmux.send_key(name, "Enter")


# --- Der Brain: fester Ansprechpartner ---------------------------------------

# Die Starter-Ausstattung für einen frischen Brain (Landkarte + Rollen-Anweisung).
BRAIN_STARTER = Path(__file__).resolve().parent.parent / "deploy" / "brain-starter"

BRAIN_BEGRUESSUNG = (
    "Begrüße mich kurz und herzlich als mein Brain — mein fester Überblick und "
    "Ansprechpartner hier. Erkläre in wenigen, einfachen Sätzen ohne Fachbegriffe: "
    "Ich kann auf diesem Server so lange arbeiten, wie ich will; alles, was wir "
    "tun, hältst du in deiner Landkarte fest; und ich starte ein neues Vorhaben, "
    "indem ich dir einfach sage, was ich vorhabe. Halte es kurz."
)


def _brain_ordner() -> Path:
    """~/projekte/Brain sicherstellen — mit Starter-Vorlage, wenn frisch.

    Bestehendes wird NIE überschrieben: Auf einem gewachsenen Server hat der
    Brain längst seine eigene Landkarte; die bleibt unangetastet.
    """
    ordner = Path.home() / "projekte" / "Brain"
    frisch = not ordner.exists()
    ordner.mkdir(parents=True, exist_ok=True)
    if BRAIN_STARTER.is_dir():
        for quelle in BRAIN_STARTER.iterdir():
            ziel = ordner / quelle.name
            if not ziel.exists():
                shutil.copy(quelle, ziel)
    if frisch:
        subprocess.run(["git", "init", "--quiet", str(ordner)], capture_output=True)
    return ordner


@app.post("/api/brain", dependencies=[Depends(require_auth)])
async def brain_oeffnen() -> dict:
    """Den Brain öffnen — den festen Ansprechpartner.

    Ein Knopf für alle Fälle: Läuft der Brain, wird er genommen; schläft oder
    stürzte er ab, wird er geweckt; gibt es ihn noch gar nicht (frischer
    Server), wird er angelegt — angeheftet und mit einer Begrüßung. So kann der
    Brain nie verloren gehen.
    """
    ordner = await asyncio.to_thread(_brain_ordner)
    ordner_str = str(ordner)

    vorhanden = next(
        (e for e in state.overview() if e["cwd"] == ordner_str and e["eigen"]),
        None,
    )
    if vorhanden:
        name = vorhanden["name"]
        if vorhanden["state"] in (state.SLEEPING, state.CRASHED):
            meta = state.get(name)
            try:
                # Wie session_wecken: mit der gemerkten Gesprächs-Kennung
                # GENAU dieses Gespräch fortsetzen. Die Kennung bleibt
                # stehen — siehe dort, warum.
                tmux.create(name, ordner_str, ohne_rueckfragen=meta.ohne_rueckfragen,
                            fortsetzen=True, gespraech=meta.mitschrift)
            except tmux.TmuxError as error:
                raise HTTPException(409, str(error))
        state.update(name, pinned=True, schlaeft=False, archiviert=False)
        return {"name": name, "neu": False}

    # Kein Brain da — einen frischen anlegen, angeheftet und mit Begrüßung.
    name = "Brain"
    try:
        tmux.create(name, ordner_str)
    except tmux.TmuxError as error:
        raise HTTPException(409, str(error))
    state.update(name, pinned=True, created_prompt=BRAIN_BEGRUESSUNG,
                 cwd=ordner_str, schlaeft=False)
    asyncio.create_task(_ersten_auftrag_schicken(name, BRAIN_BEGRUESSUNG))
    return {"name": name, "neu": True}


@app.patch("/api/sessions/{name}", dependencies=[Depends(require_auth)])
def patch_session(name: str, body: Patch) -> dict:
    # Auch eine schlafende oder abgestürzte Sitzung darf man anheften oder
    # umbenennen — sie hat nur kein Terminal, aber sehr wohl eine Karte in der
    # Liste. Beide erkennt man am gemerkten Ordner, ob sanft eingeschlafen
    # oder abgerissen spielt hier keine Rolle.
    if not tmux.exists(name) and not state.get(name).cwd:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    changes = {}
    if body.pinned is not None:
        changes["pinned"] = body.pinned
    if body.notify_when_done is not None:
        changes["notify_when_done"] = body.notify_when_done
    if body.anzeige is not None:
        # Ein leerer Name heißt: zurück zum technischen Namen.
        changes["anzeige"] = body.anzeige.strip()[:60]
    if body.archiviert is not None:
        changes["archiviert"] = body.archiviert

    meta = state.update(name, **changes)
    return {
        "ok": True,
        "pinned": meta.pinned,
        "notifyWhenDone": meta.notify_when_done,
        "anzeige": meta.anzeige,
        "archiviert": meta.archiviert,
    }


@app.delete("/api/sessions/{name}", dependencies=[Depends(require_auth)])
def delete_session(name: str) -> dict:
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        # Eine schlafende oder abgestürzte Sitzung hat kein Terminal mehr —
        # löschen heißt hier nur noch: die Karte und das Gemerkte wegräumen.
        if state.get(name).cwd:
            state.forget(name)
            return {"ok": True}
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    # Fremde Sitzungen — etwa die, in der Claude Code selbst läuft — darf man
    # ansehen und bedienen, aber nicht abschießen. Sonst legt man sich mit
    # einem Fingertipp die eigene Arbeitsumgebung lahm.
    if not treffer[0].eigen:
        raise HTTPException(403, "Diese Sitzung gehört nicht der App — sie bleibt.")

    tmux.kill(name)
    state.forget(name)
    return {"ok": True}


@app.post("/api/sessions/{name}/schlafen", dependencies=[Depends(require_auth)])
def session_schlafen(name: str) -> dict:
    """Die Sitzung schlafen legen: Terminal beenden, Speicher freigeben.

    Das Gespräch bleibt auf der Platte; die Karte bleibt in der Liste und
    wacht auf Antippen wieder auf. Der Sinn: Jede offene Claude-Sitzung hält
    ein paar hundert MB fest — auf der kleinen Maschine wird das schnell eng,
    wenn mehrere Projekte zugleich offen stehen (so starb am 17.07. das Brain).
    """
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    if not treffer[0].eigen:
        raise HTTPException(403, "Diese Sitzung gehört nicht der App — sie bleibt.")

    # Mitten in der Arbeit wird nicht geschlafen: Ein Abriss jetzt hieße, dass
    # Claude einen halb ausgeführten Auftrag liegen lässt.
    if state.detect(name) == state.RUNNING:
        raise HTTPException(409, "Claude arbeitet dort gerade — erst fertig arbeiten lassen oder anhalten.")

    # Festhalten, was zum Aufwecken gebraucht wird — und wie die Karte zuletzt
    # aussah, damit sie nicht leer in der Liste steht.
    state.update(
        name,
        schlaeft=True,
        cwd=treffer[0].cwd,
        schlaf_zeit=int(time.time()),
        letzte_vorschau=state.preview(name),
    )
    tmux.kill(name)
    return {"ok": True}


@app.post("/api/sessions/{name}/wecken", dependencies=[Depends(require_auth)])
def session_wecken(name: str) -> dict:
    """Eine schlafende oder abgestürzte Sitzung aufwecken — mit ihrem alten Gespräch.

    Claude startet im gemerkten Ordner und setzt dort das jüngste Gespräch
    fort. Der Startmodus (fragt / fragt nie) bleibt, wie er beim Anlegen war.
    Ob die Sitzung sanft eingeschlafen ist oder abgestürzt, macht hier keinen
    Unterschied — in beiden Fällen ist nur der Ordner gemerkt, kein Terminal.
    """
    meta = state.get(name)
    if tmux.exists(name):
        # Schon wach — etwa von Hand neu gestartet. Dann nur die Merker lösen.
        state.update(name, schlaeft=False, archiviert=False)
        return {"ok": True}
    if not meta.cwd:
        raise HTTPException(404, "Für diese Sitzung ist kein Ordner gemerkt.")
    if not Path(meta.cwd).is_dir():
        raise HTTPException(409, f"Den Ordner {meta.cwd} gibt es nicht mehr.")

    try:
        # Mit der gemerkten Gesprächs-Kennung wacht GENAU dieses Gespräch auf
        # (--resume) — nicht blind das jüngste des Ordners, das seit den
        # getrennten Karten auch ein Nachbar-Chat sein kann.
        tmux.create(name, meta.cwd, ohne_rueckfragen=meta.ohne_rueckfragen,
                    fortsetzen=True, gespraech=meta.mitschrift)
    except tmux.TmuxError as error:
        raise HTTPException(409, str(error))

    # Wer aufwacht, gehört wieder in die Liste — auch wenn er im Archiv lag.
    #
    # Die Gesprächs-Kennung BLEIBT. Früher wurde sie hier gelöst, in der
    # Annahme, das Fortsetzen lege eine neue Mitschrift-Datei an. Das tut
    # Claude Code seit Sommer 2026 nicht mehr: --resume schreibt in dieselbe
    # Datei weiter. Gelöst hieß: Die geweckte Karte hing ohne Bindung in der
    # Luft und zeigte alles, was im Ordner seither geschrieben wurde — auch
    # den Nachbar-Chat (Rolis Fund 25.08.: „Marketing" und „Skillsradar 01"
    # zusammengewachsen). Sollte das Fortsetzen doch einmal woanders landen
    # (Datei gelöscht, Rückfall auf --continue), greift die Einfrier-Erkennung
    # in _mitschrift_zuordnen und bindet neu.
    state.update(name, schlaeft=False, archiviert=False)
    return {"ok": True}


@app.get("/api/dirs", dependencies=[Depends(require_auth)])
def list_dirs() -> list[str]:
    """Ordnervorschläge fürs Neue-Sitzung-Formular.

    Auf dem Handy will niemand einen Pfad tippen — man tippt ihn an.
    """
    root = Path(os.environ.get("HETZNER_APP_PROJECTS", Path.home() / "projekte"))
    if not root.is_dir():
        return [str(Path.home())]

    dirs = sorted(
        (d for d in root.iterdir() if d.is_dir() and not d.name.startswith(".")),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    return [str(d) for d in dirs[:20]]


# --- Benachrichtigungen ------------------------------------------------------

@app.get("/api/melden/schluessel", dependencies=[Depends(require_auth)])
def melden_schluessel() -> dict:
    """Den der Browser braucht, um sich beim Push-Dienst anzumelden."""
    return {"schluessel": melden.oeffentlicher_schluessel()}


# Die Hosts der bekannten Browser-Push-Dienste. Der Server schickt später POSTs
# an die endpoint-URL der Anmeldung — nähme er dafür ein ungeprüftes dict (wie
# früher), könnte ein angemeldetes Gerät die URL auf interne Adressen zeigen
# lassen (127.0.0.1, Cloud-Metadaten 169.254.169.254) und den Server als
# Sprungbrett missbrauchen. Darum nur echte Push-Gateways zulassen. Ein Eintrag
# mit führendem Punkt gilt als Domain-Suffix, einer ohne als exakter Host.
_PUSH_HOSTS = (
    "fcm.googleapis.com",
    "android.googleapis.com",
    ".push.services.mozilla.com",
    ".notify.windows.com",
    ".push.apple.com",
)


def _push_host_erlaubt(host: str) -> bool:
    host = host.lower()
    return any(host.endswith(h) if h.startswith(".") else host == h
               for h in _PUSH_HOSTS)


class PushSchluessel(BaseModel):
    p256dh: str = Field(min_length=1, max_length=200)
    auth: str = Field(min_length=1, max_length=100)


class PushAnmeldung(BaseModel):
    endpoint: str = Field(min_length=1, max_length=1000)
    keys: PushSchluessel
    expirationTime: float | None = None

    @field_validator("endpoint")
    @classmethod
    def _endpoint_pruefen(cls, wert: str) -> str:
        ziel = urlparse(wert)
        if ziel.scheme != "https" or not ziel.hostname:
            raise ValueError("endpoint muss eine https-Adresse sein")
        if not _push_host_erlaubt(ziel.hostname):
            raise ValueError("endpoint zeigt nicht auf einen bekannten Push-Dienst")
        return wert


@app.post("/api/melden/eintragen", dependencies=[Depends(require_auth)])
async def melden_eintragen(anmeldung: PushAnmeldung) -> dict:
    melden.eintragen(anmeldung.model_dump(exclude_none=True))
    return {"ok": True}


@app.post("/api/melden/probe", dependencies=[Depends(require_auth)])
def melden_probe() -> dict:
    """Eine Probenachricht — damit du siehst, dass es wirklich ankommt."""
    zugestellt = melden.schicken(
        "Probe",
        "Die Benachrichtigungen funktionieren. Ab jetzt meldet sich dein Handy, wenn Claude fertig ist.",
    )
    return {"ok": True, "zugestellt": zugestellt}


# --- Vorlesen ----------------------------------------------------------------

class Speak(BaseModel):
    text: str
    stimme: str | None = None      # nur für die Hörprobe


class Stimme(BaseModel):
    name: str


@app.post("/api/speak", dependencies=[Depends(require_auth)])
async def speak(body: Speak) -> Response:
    # Leeren Text gar nicht erst zu Piper tragen — der lehnte ihn nur ab, und
    # die alte Neustart-Logik warf dafür sogar das warme Modell weg.
    if not body.text.strip():
        raise HTTPException(400, "Kein Text zum Vorlesen.")
    # Obergrenze: Vorlesen ist fürs Ohr — niemand hört sich 100.000 Zeichen
    # an, aber Piper würde Minuten daran rechnen.
    if len(body.text) > 100_000:
        raise HTTPException(413, "Der Text zum Vorlesen ist zu lang.")
    try:
        audio = await tts.synthesize(body.text, body.stimme)
    except tts.TTSError as fehler:
        # Eine verständliche Meldung statt eines nackten 500ers.
        raise HTTPException(503, str(fehler))
    return Response(content=audio, media_type="audio/wav")


@app.get("/api/stimmen", dependencies=[Depends(require_auth)])
def stimmen() -> list[dict]:
    """Welche Stimmen bereitliegen — und welche gerade spricht."""
    return tts.stimmen()


@app.post("/api/stimmen", dependencies=[Depends(require_auth)])
def stimme_waehlen(body: Stimme) -> dict:
    try:
        tts.stimme_waehlen(body.name)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))
    return {"ok": True, "stimme": body.name}


# Schützt Prüfen-und-Setzen der Gesprächs-Zuordnung: Ohne Sperre konnten zwei
# gleichzeitig pollende Sitzungen dieselbe Mitschrift zugewiesen bekommen
# (beide lasen die Vergeben-Liste, bevor der jeweils andere schrieb).
_zuordnung_sperre = threading.Lock()

# Nur wer in diesem Zeitraum geschrieben hat, gilt als „gerade aktiv" —
# für Terminals wie für Mitschrift-Dateien.
_ZUORDNUNG_FRISCH_S = 15

# Ist die gebundene Datei so lange still, während das Terminal munter
# schreibt, hat drinnen ein NEUES Gespräch begonnen (/clear, Absturz mit
# frischem Start) — dann darf die Erkennung neu binden.
_ZUORDNUNG_EINGEFROREN_S = 300


def _mitschrift_zuordnen(s: tmux.TmuxSession) -> str:
    """Welches Gespräch gehört diesem Terminal? Erkannt und dauerhaft gemerkt.

    Den Claude-Prozess fragen können wir nicht (er kennt seine Kennung selbst
    nicht), also lesen wir die Schreib-Spur: Wurde in den letzten Sekunden
    GENAU EINE noch unvergebene Mitschrift beschrieben, während dieses
    Terminal als EINZIGES im Ordner aktiv war, gehören die beiden zusammen.
    Bei jeder Unklarheit (zwei frische Dateien, Terminal still, ein Nachbar —
    auch ein fremdes Terminal wie die Fernbedienung — war zeitgleich aktiv)
    wird NICHT geraten — dann eben beim nächsten Mal.

    Eine bestehende Bindung wird nur in zwei Fällen angefasst: Die Datei ist
    verschwunden (gelöscht), oder sie liegt seit Minuten still, während das
    Terminal munter schreibt — dann läuft drinnen längst ein neues Gespräch
    (/clear, frischer Start nach Absturz), und der Verlauf fröre sonst für
    immer ein (Fund der Code-Durchsicht 20.08.).
    """
    meta = state.get(s.name)
    jetzt = time.time()
    ordner = mitschrift.PROJEKTE / mitschrift._ordnername(s.cwd)
    terminal_aktiv = jetzt - s.last_activity < _ZUORDNUNG_FRISCH_S

    if meta.mitschrift:
        try:
            datei_alter = jetzt - (ordner / f"{meta.mitschrift}.jsonl").stat().st_mtime
        except OSError:
            datei_alter = None                      # Datei weg — Bindung lösen
        if datei_alter is None:
            state.update(s.name, mitschrift="")
            meta = state.get(s.name)
        elif not (terminal_aktiv and datei_alter > _ZUORDNUNG_EINGEFROREN_S):
            return meta.mitschrift                  # Bindung passt weiter
        # sonst: eingefroren — unten neu erkennen; bis dahin bleibt die alte
        # Bindung stehen (besser das alte Gespräch als geratenes fremdes).

    if not terminal_aktiv or not ordner.is_dir():
        return meta.mitschrift

    # Nur binden, wenn dieses Terminal das EINZIGE gerade aktive im Ordner
    # ist — sonst könnte die frische Datei dem Nachbarn gehören.
    for andere in tmux.list_sessions():
        if (andere.cwd == s.cwd and andere.name != s.name
                and jetzt - andere.last_activity < _ZUORDNUNG_FRISCH_S):
            return meta.mitschrift

    with _zuordnung_sperre:
        vergeben = state.vergebene_mitschriften()
        frische = []
        for datei in ordner.glob("*.jsonl"):
            if datei.stem in vergeben:
                continue
            try:
                if jetzt - datei.stat().st_mtime < _ZUORDNUNG_FRISCH_S:
                    frische.append(datei.stem)
            except OSError:
                continue
        if len(frische) != 1:
            return meta.mitschrift
        state.update(s.name, mitschrift=frische[0])
        return frische[0]


def _gespraechs_bloecke(s: tmux.TmuxSession) -> list[dict]:
    """Die Mitschrift-Blöcke, die zu DIESEM Terminal gehören.

    Eigene Terminals sind je EIN Gespräch: erst über die gemerkte Kennung,
    solange die fehlt nur das, was seit dem Start dieses Terminals
    geschrieben wurde — nichts von den Nachbarn im selben Ordner erben
    (Rolis Fund 20.08.: zwei Chats im selben Projekt zeigten denselben
    Verlauf). Fremde Terminals behalten die Projekt-Zeitleiste.
    """
    if s.eigen:
        datei = _mitschrift_zuordnen(s)
        if datei:
            return mitschrift.lesen(s.cwd, datei=datei)
        # Übergang ohne Bindung: nur, was seit dem Start geschrieben wurde —
        # und nichts, was schon einer anderen Karte gehört.
        return mitschrift.lesen(s.cwd, seit=s.created,
                                ausser=state.vergebene_mitschriften())
    return mitschrift.lesen(s.cwd)


@app.get("/api/sessions/{name}/text", dependencies=[Depends(require_auth)])
def session_text(name: str) -> dict:
    """Claudes letzte Antwort DIESES Gesprächs, zum Vorlesen."""
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    # Aus der Mitschrift, nicht vom Bildschirm: Dort steht die Antwort ganz,
    # nicht nur der Teil, der gerade zu sehen ist. Sie steht dort als Markdown —
    # ungefiltert vorgelesen wird daraus Kauderwelsch aus Sternchen und Rauten.
    for block in reversed(_gespraechs_bloecke(treffer[0])):
        if block["typ"] == "claude" and block["text"].strip():
            gesprochen = tts.fuer_stimme(block["text"])
            if gesprochen:
                return {"text": gesprochen}

    # Keine Mitschrift? Dann eben doch vom Bildschirm.
    return {"text": tts.for_speech(tmux.capture(name, lines=200))}


@app.get("/api/sessions/{name}/verlauf", dependencies=[Depends(require_auth)])
def session_verlauf(name: str) -> list[dict]:
    """Die Unterhaltung DIESES Gesprächs.

    Nicht vom Terminal-Bildschirm abgelesen und geraten: Claude Code schreibt
    jede Sitzung ohnehin mit, vollständig und sauber getrennt nach Sprecher.
    Seit jedes Gespräch seine eigene Karte hat (20.08.), gilt: ein Verlauf je
    GESPRÄCH — die alte Projekt-Zeitleiste gibt es nur noch für fremde
    Terminals und als Übergang, solange die Zuordnung noch nicht erkannt ist.
    """
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    bloecke = _gespraechs_bloecke(treffer[0])

    # Findet sich keine Mitschrift — etwa bei einem Ordner, in dem Claude Code
    # noch nie lief —, lesen wir notfalls doch den Bildschirm ab. Besser als
    # eine leere Seite.
    if not bloecke:
        return verlauf.lesen(tmux.capture(name, lines=5000))

    return bloecke


# Was wir annehmen. Alles andere fliegt raus — hier landet nichts Ausführbares.
BILDARTEN = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/heic": ".heic",
}

MAX_BILD = 20 * 1024 * 1024      # 20 MB


@app.post("/api/sessions/{name}/bild", dependencies=[Depends(require_auth)])
async def session_bild(name: str, bild: UploadFile = File(...)) -> dict:
    """Ein Foto an Claude schicken.

    Claude Code kann Bilder von der Festplatte lesen. Also legen wir das Foto
    dort ab und reichen den Pfad in die Sitzung — so, wie man ihn am Rechner
    selbst eintippen würde.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    endung = BILDARTEN.get(bild.content_type or "")
    if not endung:
        raise HTTPException(400, "Das ist kein Bild, das ich annehmen kann.")

    inhalt = await bild.read()
    if len(inhalt) > MAX_BILD:
        raise HTTPException(413, "Das Bild ist zu groß (mehr als 20 MB).")

    # Das Foto landet im Arbeitsordner der Sitzung.
    #
    # Nicht in einem eigenen Bilderordner: Claude Code fragt dann bei jedem
    # Bild um Leseerlaubnis, und das wäre bei jedem Foto eine Rückfrage. In
    # seinem eigenen Arbeitsordner darf er ohne Weiteres lesen.
    sitzung = [s for s in tmux.list_sessions() if s.name == name][0]
    arbeitsordner = Path(sitzung.cwd)

    # Sicherheitsnetz: Meldet eine Sitzung einen unbrauchbaren Arbeitsordner —
    # etwa "/" —, legen wir dort nichts an. Dort haben wir nichts zu suchen,
    # und es scheiterte auch nur mit einer kryptischen Fehlermeldung.
    if not arbeitsordner.is_dir() or not os.access(arbeitsordner, os.W_OK):
        raise HTTPException(
            400,
            "In den Ordner dieser Sitzung darf ich nicht schreiben. "
            "Schick das Bild aus einer Sitzung, die in einem Projektordner läuft.",
        )

    ordner = arbeitsordner / ".hetzner-bilder"
    ordner.mkdir(parents=True, exist_ok=True)

    # Damit die Fotos nicht in Git landen.
    hinweis = ordner / ".gitignore"
    if not hinweis.exists():
        hinweis.write_text("*\n")

    # Der Dateiname kommt von uns, nicht aus dem Netz.
    ziel = ordner / f"{int(time.time())}-{secrets.token_hex(4)}{endung}"
    ziel.write_bytes(inhalt)

    # Der kurze, relative Pfad — nicht der lange absolute.
    #
    # Claude Code arbeitet ohnehin in diesem Ordner und findet die Datei so
    # genauso. Der lange Pfad dagegen bricht im Terminal über zwei Zeilen um,
    # und dann erkennt die App ihn nicht mehr als Bild, sondern zeigt dir
    # Buchstabensalat.
    return {"ok": True, "pfad": f".hetzner-bilder/{ziel.name}"}


# Dokumente, die wir annehmen. Ausführbares und Unbekanntes bleibt draußen —
# gelesen wird die Datei zwar nur, aber wir legen nichts Beliebiges im Projekt
# ab. Die Endung bleibt erhalten, damit Claude Code weiß, was es vor sich hat.
# ZIP ist die eine Ausnahme von "nichts Undurchsichtiges": Das Archiv wird hier
# nur abgelegt, nicht entpackt — hineingeschaut wird erst in der Sitzung, auf
# Ansage und mit Blick auf den Inhalt.
DOK_ENDUNGEN = {
    ".pdf", ".md", ".markdown", ".txt", ".text", ".rtf",
    ".doc", ".docx", ".odt", ".csv", ".tsv",
    ".xls", ".xlsx", ".ods", ".ppt", ".pptx",
    ".json", ".yaml", ".yml", ".log", ".xml", ".html",
    ".zip",
}

MAX_DATEI = 30 * 1024 * 1024      # 30 MB — Dokumente sind schwerer als Fotos


@app.post("/api/sessions/{name}/datei", dependencies=[Depends(require_auth)])
async def session_datei(name: str, datei: UploadFile = File(...)) -> dict:
    """Ein Dokument an Claude schicken — PDF, Word, Markdown, Text, Tabellen.

    Wie beim Foto: Wir legen die Datei im Arbeitsordner der Sitzung ab und
    reichen den kurzen Pfad hinein. Claude Code liest sie dann von der Platte.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    endung = Path(datei.filename or "").suffix.lower()
    if endung not in DOK_ENDUNGEN:
        raise HTTPException(
            400,
            "Diese Dateiart nehme ich nicht an. Erlaubt sind PDF, Word, "
            "Markdown, Text, Tabellen, ZIP-Archive und ähnliche Dokumente.",
        )

    inhalt = await datei.read()
    if len(inhalt) > MAX_DATEI:
        raise HTTPException(413, "Die Datei ist zu groß (mehr als 30 MB).")

    sitzung = [s for s in tmux.list_sessions() if s.name == name][0]
    arbeitsordner = Path(sitzung.cwd)
    if not arbeitsordner.is_dir() or not os.access(arbeitsordner, os.W_OK):
        raise HTTPException(
            400,
            "In den Ordner dieser Sitzung darf ich nicht schreiben. "
            "Schick die Datei aus einer Sitzung, die in einem Projektordner läuft.",
        )

    # Ein eigener Ordner für Anhänge, damit sie sich nicht mit den Projektdateien
    # mischen — und nicht in Git landen.
    ordner = arbeitsordner / ".hetzner-dateien"
    ordner.mkdir(parents=True, exist_ok=True)
    hinweis = ordner / ".gitignore"
    if not hinweis.exists():
        hinweis.write_text("*\n")

    # Der Dateiname kommt von uns; nur die Endung stammt aus dem Netz, und die
    # haben wir gegen die Positivliste geprüft.
    ziel = ordner / f"{int(time.time())}-{secrets.token_hex(4)}{endung}"
    ziel.write_bytes(inhalt)

    return {"ok": True, "pfad": f".hetzner-dateien/{ziel.name}"}


@app.get("/api/bilder/{sitzung}/{datei}", dependencies=[Depends(require_auth)])
def bild_zeigen(sitzung: str, datei: str) -> FileResponse:
    """Ein geschicktes Foto wieder anzeigen.

    Nur Dateien aus dem Bilderordner der genannten Sitzung. Der Name kommt aus
    dem Netz, und "../../etc/passwd" wäre sonst eine gültige Anfrage.
    """
    treffer = [s for s in tmux.list_sessions() if s.name == sitzung]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    ordner = (Path(treffer[0].cwd) / ".hetzner-bilder").resolve()
    ziel = (ordner / datei).resolve()

    # Der aufgelöste Pfad muss wirklich in diesem Ordner liegen — sonst hat
    # jemand mit "../" die Schranke umfahren.
    if not ziel.is_file() or ziel.parent != ordner:
        raise HTTPException(404, "Dieses Bild gibt es nicht.")

    return FileResponse(ziel)


class Nachricht(BaseModel):
    text: str


class Modell(BaseModel):
    name: str


# Was Claude Code versteht — und was ein Mensch darunter versteht.
# Die Kurznamen links sind die, die `claude --model` annimmt; die Zahlen dahinter
# ändern sich mit jeder Modellgeneration, die Kurznamen nicht.

# Namen ohne Versionsnummer, absichtlich: "/model opus" u.ä. sind Aliase, die
# Claude Code selbst immer auf die neueste Version dieser Familie auflöst
# (Stand 2.1.220). Stünde hier "Opus 4.8" fest im Text, veraltete das Etikett
# bei jedem neuen Claude-Modell, obwohl die Auswahl technisch längst die
# neueste Version trifft — genau das hat Roli am 02.08. verwirrt.
# Jeder Eintrag: Kurzname/voller Name → (Anzeige, Beschreibung, Gruppe).
# Gruppe "aktuell" sind die Alias-Kurznamen (immer die neueste Version ihrer
# Familie). Gruppe "weitere" sind ältere, fest gepinnte Versionen zum
# Ausweichen, falls die ganze neueste Generation gerade gestört ist — genau
# das ist am 18.08.2026 passiert (Anthropic-Ausfall, alle 5er-Modelle weg,
# und in der App gab es keinen Weg auf ein älteres). Hier stehen die VOLLEN
# Namen, weil die Kurznamen sonst wieder auf die (ausgefallene) neueste
# Version zeigten. Die Namen sind aus Claude Codes eigener History verifiziert.
# Ein unbekannter Name lässt /model das laufende Modell behalten und meldet
# nur einen Fehler — eine hier veraltete Zeile ist also ungefährlich, nicht
# kaputt. Prüfen, wenn eine neue Modellgeneration erscheint.
MODELLE = {
    "fable": ("Fable", "das neueste", "aktuell"),
    "opus": ("Opus", "am stärksten, verbraucht die Limits schneller", "aktuell"),
    "sonnet": ("Sonnet", "am effizientesten für Alltagsaufgaben", "aktuell"),
    "haiku": ("Haiku", "am schnellsten für kurze Antworten", "aktuell"),
    "claude-opus-4-8": ("Opus 4.8", "ältere Version — Ausweichen bei Störung", "weitere"),
    "claude-opus-4-7": ("Opus 4.7", "ältere Version", "weitere"),
    "claude-opus-4-6": ("Opus 4.6", "ältere Version", "weitere"),
    "claude-sonnet-4-6": ("Sonnet 4.6", "ältere Version — schlanker", "weitere"),
}


# --- Routinen: was auf dem Server von selbst läuft ---------------------------

_ROUTINE_KENNUNG = re.compile(r"^[0-9a-f]{10}$")


def _routine_kennung(kennung: str) -> str:
    """Nur Kennungen von Cron-Zeilen dürfen etwas auslösen — die Timer
    (Kennung „t-…") gehören root und werden nur angezeigt."""
    if not _ROUTINE_KENNUNG.match(kennung):
        raise HTTPException(400, "Diese Routine lässt sich hier nicht steuern.")
    return kennung


@app.get("/api/routinen", dependencies=[Depends(require_auth)])
async def routinen_liste() -> list:
    """Alle Zeitpläne dieses Kontos: crontab und eigene systemd-Timer."""
    return await asyncio.to_thread(routinen.lesen)


@app.post("/api/routinen/{kennung}/jetzt", dependencies=[Depends(require_auth)])
async def routine_jetzt(kennung: str) -> dict:
    try:
        return await asyncio.to_thread(routinen.jetzt_ausfuehren, _routine_kennung(kennung))
    except KeyError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.post("/api/routinen/{kennung}/pause", dependencies=[Depends(require_auth)])
async def routine_pause(kennung: str) -> dict:
    try:
        return await asyncio.to_thread(routinen.pausieren, _routine_kennung(kennung), True)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.post("/api/routinen/{kennung}/weiter", dependencies=[Depends(require_auth)])
async def routine_weiter(kennung: str) -> dict:
    try:
        return await asyncio.to_thread(routinen.pausieren, _routine_kennung(kennung), False)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.get("/api/routinen/{kennung}/protokoll", dependencies=[Depends(require_auth)])
async def routine_protokoll(kennung: str) -> dict:
    if not (_ROUTINE_KENNUNG.match(kennung) or re.match(r"^t-[a-z0-9-]{1,80}$", kennung)):
        raise HTTPException(400, "Unbekannte Kennung.")
    try:
        return await asyncio.to_thread(routinen.protokoll, kennung)
    except KeyError as e:
        raise HTTPException(404, str(e))


@app.get("/api/speicher", dependencies=[Depends(require_auth)])
def speicher_stand() -> dict:
    """Der letzte Stand des Speicher-Wächters — für die Ampel oben in der App.

    Gemessen wird nicht hier, sondern vom systemd-Timer (speicher-waechter);
    wir reichen nur seine letzte Messung durch. Gibt es (noch) keine, sagen
    wir das ehrlich, statt selbst zu messen — sonst merkte niemand, dass der
    Wächter gar nicht läuft.
    """
    stand = speicher.lesen()
    return stand if stand else {"ampel": None}


@app.get("/api/modelle", dependencies=[Depends(require_auth)])
def modelle() -> list[dict]:
    return [
        {"name": name, "anzeige": anzeige, "art": art, "gruppe": gruppe}
        for name, (anzeige, art, gruppe) in MODELLE.items()
    ]


@app.post("/api/sessions/{name}/modell", dependencies=[Depends(require_auth)])
async def modell_wechseln(name: str, body: Modell) -> dict:
    """Das Modell dieser Sitzung wechseln.

    Für eine schnelle Frage braucht es kein Opus. Claude Code kennt dafür den
    Befehl /model — wir tippen ihn nur, statt dass du es unterwegs tun musst.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    if body.name not in MODELLE:
        raise HTTPException(400, "Dieses Modell kenne ich nicht.")

    tmux.send_text(name, f"/model {body.name}")
    await asyncio.sleep(0.4)
    tmux.send_key(name, "Enter")

    # Claude Code bestätigt selbst, welches Modell der Alias getroffen hat
    # ("Set model to Opus 5 …") — das lesen wir mit, statt im Code eine
    # Versionsnummer zu raten, die beim nächsten Modell-Release schon wieder
    # veraltet wäre.
    aufgeloest = await asyncio.to_thread(state.modell_bestaetigung, name)
    state.update(name, modell=body.name, modell_aufgeloest=aufgeloest)
    return {"ok": True, "modell": body.name, "modellAufgeloest": aufgeloest}


# --- Die Bibliothek ----------------------------------------------------------

class SkillEtikett(BaseModel):
    id: str
    name: str = ""
    beschreibung: str = ""
    kategorie: str = ""


@app.get("/api/skills", dependencies=[Depends(require_auth)])
def skills() -> list[dict]:
    """Alle Skills — mit deinem deutschen Etikett, wo du eins vergeben hast."""
    return bibliothek.liste()


@app.patch("/api/skills", dependencies=[Depends(require_auth)])
def skill_etikett(body: SkillEtikett) -> dict:
    """Deinen Namen, deine Beschreibung, deine Kategorie über einen Skill legen.

    Die Kennung kommt aus dem Netz — also prüfen wir, dass es den Skill
    wirklich gibt, statt beliebige Einträge in den Speicher zu schreiben.
    """
    if body.id not in {s["id"] for s in bibliothek.liste()}:
        raise HTTPException(404, "Diesen Skill gibt es nicht.")

    bibliothek.setzen(body.id, body.name, body.beschreibung, body.kategorie)
    return {"ok": True}


class NeuerSkill(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    beschreibung: str = ""
    anleitung: str = ""


@app.post("/api/skills/neu", dependencies=[Depends(require_auth)])
def skill_neu(body: NeuerSkill) -> dict:
    """Einen eigenen Skill aus getipptem oder diktiertem Text anlegen."""
    try:
        kennung = bibliothek.neu_aus_text(body.name, body.beschreibung, body.anleitung)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))
    return {"ok": True, "id": kennung}


@app.post("/api/skills/hochladen", dependencies=[Depends(require_auth)])
async def skill_hochladen(
    datei: UploadFile = File(...),
    name: str = Form(""),
) -> dict:
    """Einen Skill aus einer Datei anlegen — eine SKILL.md oder ein .zip."""
    inhalt = await datei.read()
    if len(inhalt) > 5 * 1024 * 1024:      # 5 MB reicht für Text und Beiwerk
        raise HTTPException(413, "Die Datei ist zu groß (mehr als 5 MB).")

    try:
        kennung = bibliothek.neu_aus_datei(datei.filename or "", inhalt, name)
    except ValueError as fehler:
        raise HTTPException(400, str(fehler))
    return {"ok": True, "id": kennung}


class Antwort(BaseModel):
    nummer: int


@app.get("/api/sessions/{name}/frage", dependencies=[Depends(require_auth)])
def session_frage(name: str) -> dict:
    """Hängt die Sitzung gerade an einer Rückfrage? Dann hier, mit Antworten.

    Huckepack fährt der Anmelde-Link mit: Steht auf dem Bildschirm eine
    OAuth-Adresse von Claude Code (nach "/login"), liefern wir sie als
    anmeldeLink — die App macht daraus einen Öffnen-Knopf, statt dass man
    die Adresse aus dem Terminal abtippen muss. Im selben Aufruf, weil die
    App hier ohnehin alle paar Sekunden nachschaut.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    antwort = state.frage(name) or {}
    link = state.anmelde_link(name)
    if link:
        antwort["anmeldeLink"] = link
    return antwort


@app.post("/api/ton-tagebuch", dependencies=[Depends(require_auth)])
async def ton_tagebuch(request: Request) -> dict:
    """Das Ton-Tagebuch — Protokoll fürs Jagen der Hosentaschen-Abbrüche.

    Die App funkt beim Vorlesen jedes wichtige Ereignis hierher (Ton
    angehalten, Weckversuch, System-Pause …). Landet als eine Zeile je
    Ereignis in ~/.hetzner-app/ton-tagebuch.log — zum Nachlesen, wer den
    Vortrag wirklich beendet hat. Wird die Datei zu groß, beginnt sie neu.

    Standardmäßig AUS (Telemetrie-Sorge bei Weitergabe) — dann nichts
    geschrieben, nichts gespeichert. Einschalten über die Umgebung.
    """
    if not TON_TAGEBUCH_AN:
        return {"ok": True}          # aus: nichts protokollieren
    datei = Path.home() / ".hetzner-app" / "ton-tagebuch.log"
    try:
        koerper = (await request.body())[:2000].decode("utf-8", "replace")
    except Exception:
        koerper = "?"
    try:
        if datei.exists() and datei.stat().st_size > 1_000_000:
            datei.unlink()
        with open(datei, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%d.%m. %H:%M:%S')} {koerper}\n")
    except OSError:
        pass                     # das Tagebuch darf nie zum Störfall werden
    return {"ok": True}


@app.get("/api/sessions/{name}/verbrauch", dependencies=[Depends(require_auth)])
def session_verbrauch(name: str) -> dict:
    """Wie voll das Kontextfenster ist und wo die Plan-Limits stehen.

    Beides zusammen in einem Aufruf, weil die App beides zusammen anzeigt:
    oben der Füllstand der Unterhaltung, darunter die Limits des Abos mit
    ihrer Zurücksetzungszeit. Fehlt eine Quelle, kommt dort schlicht null —
    die App zeigt dann nur, was sie ehrlich weiß.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    ordner = next(
        (s.cwd for s in tmux.list_sessions() if s.name == name), ""
    )
    return {
        "kontext": verbrauch.kontext(ordner) if ordner else None,
        "limits": verbrauch.limits(),
    }


@app.get("/api/sessions/{name}/kontext", dependencies=[Depends(require_auth)])
def session_kontext(name: str) -> dict:
    """Nur der Kontext-Füllstand — schlank, für die Daueranzeige im Kopf.

    Bewusst OHNE die Plan-Limits: Die Daueranzeige fragt oft, und die Limits
    hängen am Abo-Endpunkt (Netz, kann bei einer Störung ausfallen — genau
    dann, wenn man den Füllstand am dringendsten sehen will). Der Füllstand
    dagegen kommt aus der Mitschrift auf der Platte und ist immer da. Für die
    Details tippt man die Anzeige an und öffnet das volle Verbrauchs-Blatt.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    ordner = next((s.cwd for s in tmux.list_sessions() if s.name == name), "")
    return {"kontext": verbrauch.kontext(ordner) if ordner else None}


@app.post("/api/sessions/{name}/antwort", dependencies=[Depends(require_auth)])
def session_antwort(name: str, body: Antwort) -> dict:
    """Eine Rückfrage beantworten — so, wie man es im Terminal täte.

    Claude Code nimmt die Zifferntaste: Sie wählt und bestätigt in einem. Ein
    Enter hinterher würde nur eine leere Nachricht abschicken.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    offen = state.frage(name)
    if not offen:
        raise HTTPException(409, "Es steht gerade keine Frage offen.")
    if not any(m["nummer"] == body.nummer for m in offen["moeglichkeiten"]):
        raise HTTPException(400, "Diese Antwort gibt es zu dieser Frage nicht.")

    tmux.send_text(name, str(body.nummer))
    return {"ok": True}


@app.post("/api/sessions/{name}/modus", dependencies=[Depends(require_auth)])
async def modus_wechseln(name: str) -> dict:
    """Den Berechtigungs-Modus einen Schritt weiterschalten — wie Shift+Tab.

    Der Kreis: fragt nach → Änderungen ok → nur Plan → Auto → wieder von vorn.
    Wir tippen die Taste und lesen danach ab, wo wir gelandet sind.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    tmux.send_key(name, "BTab")
    await asyncio.sleep(0.4)
    return {"ok": True, "modus": state.modus(name)}


@app.post("/api/sessions/{name}/sichern", dependencies=[Depends(require_auth)])
def session_sichern(name: str) -> dict:
    """Den Stand dieses Projekts sichern — auf Knopfdruck.

    Kein Zeitgeber, der unbeaufsichtigt an allen Projekten arbeitet: Du drückst,
    wenn du fertig bist. Dann liegt der Stand im Lager auf dem Server, und dein
    Rechner holt ihn sich beim nächsten Hochfahren.
    """
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    ordner = Path(treffer[0].cwd)
    if not (ordner / ".git").is_dir():
        raise HTTPException(400, "Dieses Projekt hat kein Lager.")

    def git(*args: str) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                ["git", "-C", str(ordner),
                 "-c", "user.name=Hetzner-App",
                 "-c", "user.email=hetzner-app@localhost", *args],
                capture_output=True, text=True, timeout=120,
            )
        except subprocess.TimeoutExpired:
            # Hängt ein Push (Netz/DNS), nicht ewig warten und einen Thread
            # blockieren — als Fehlschlag behandeln. Der lokale Commit steht
            # ohnehin schon; die Sicherung außer Haus holt der nächste Lauf nach.
            return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="Zeitüberschreitung")

    if not git("status", "--porcelain").stdout.strip():
        return {"ok": True, "geaendert": False, "text": "Nichts zu sichern — alles ist schon gesichert."}

    git("add", "-A")
    stempel = time.strftime("%d.%m.%Y um %H:%M")
    ergebnis = git("commit", "-m", f"Vom Handy gesichert, {stempel}")
    if ergebnis.returncode != 0:
        # Die git-Meldung enthält Serverpfade und Remote-Namen — die gehören
        # ins Protokoll, nicht zum Client. Dort nur ein schlichter Hinweis.
        print(f"Sichern fehlgeschlagen: {ergebnis.stderr[:500]}", flush=True)
        raise HTTPException(500, "Sichern fehlgeschlagen — Details stehen im Server-Protokoll.")

    # Ins örtliche Lager auf dem Server schieben, falls es eins gibt.
    geschoben = git("push", "hetzner", "HEAD").returncode == 0

    # Und, wenn angebunden, zusätzlich außer Haus zu GitHub — das ist die
    # eigentliche Sicherheit: eine Kopie, die diesen Server überlebt. Scheitert
    # sie (kein Netz o. Ä.), bleibt der Stand trotzdem örtlich gesichert; daran
    # lassen wir das Sichern nicht scheitern.
    remotes = git("remote").stdout.split()
    ausser_haus = "github" in remotes and git("push", "github", "HEAD").returncode == 0

    if ausser_haus:
        text = "Gesichert — auch außer Haus bei GitHub."
    elif geschoben:
        text = ("Gesichert (örtlich). Dieses Projekt ist noch nicht bei GitHub — "
                "sag Bescheid, dann binde ich es an.")
    else:
        text = "Gesichert (nur örtlich)."

    return {"ok": True, "geaendert": True, "text": text}


@app.post("/api/sessions/{name}/abbrechen", dependencies=[Depends(require_auth)])
def session_abbrechen(name: str) -> dict:
    """Claude anhalten.

    Statt einer Antwort, die man neu erzeugen lässt: Wenn Claude in die falsche
    Richtung läuft, hält man ihn an und sagt es anders. Bei Claude Code ist das
    der richtige Griff — er *tut* ja Dinge, und die will man nicht doppelt.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    tmux.send_key(name, "Escape")
    return {"ok": True}


# --- Diktat glätten ----------------------------------------------------------

class Diktat(BaseModel):
    text: str


_GLAETTEN_PROMPT = (
    "Du glättest einen diktierten deutschen Text, der gleich an einen "
    "Programmierassistenten geschickt wird. Entferne Füllwörter (ähm, äh, halt) "
    "und Wortdopplungen, behebe offensichtliche Versprecher und Verhörer aus dem "
    "Zusammenhang, setze Satzzeichen und Großschreibung. Bewahre Sinn und "
    "Absicht des Sprechers; erfinde nichts dazu und beantworte den Text NICHT. "
    "Gib ausschließlich den bereinigten Text zurück — ohne Anführungszeichen, "
    "ohne Vorrede, ohne Erklärung."
)


def _glaetten(text: str) -> str:
    """Ruft die Claude-CLI headless auf und lässt sie den Text glätten.

    Kein API-Schlüssel nötig: Die CLI ist über dein Abo angemeldet. Wir schalten
    die MCP-Server ab — sie zu laden dauert Sekunden, und für eine reine
    Textaufgabe braucht es sie nicht. Das schnelle Haiku-Modell reicht.
    """
    claude = shutil.which("claude")
    if not claude:
        raise RuntimeError("Die claude-CLI ist nicht auffindbar.")

    eingabe = f"{_GLAETTEN_PROMPT}\n\nText: {text}"
    ergebnis = subprocess.run(
        [claude, "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
         "-p", "--model", "haiku"],
        input=eingabe, capture_output=True, text=True, timeout=30,
    )
    if ergebnis.returncode != 0:
        raise RuntimeError(ergebnis.stderr[:200] or "Die CLI meldete einen Fehler.")
    return ergebnis.stdout.strip()


# Kostenbremse fürs Glätten. Jeder Aufruf startet einen Claude-Prozess (kostet
# Token) — eine hängende Schleife im Frontend oder Missbrauch dürfen nicht
# ungebremst Aufrufe auslösen. Ein einzelner Nutzer glättet ein paar Mal pro
# Minute; alles darüber wird gebremst.
_glaetten_rufe: deque[float] = deque()
_GLAETTEN_MAX = 12
_GLAETTEN_FENSTER = 60      # Sekunden


def _glaetten_erlaubt() -> bool:
    jetzt = time.time()
    while _glaetten_rufe and _glaetten_rufe[0] < jetzt - _GLAETTEN_FENSTER:
        _glaetten_rufe.popleft()
    if len(_glaetten_rufe) >= _GLAETTEN_MAX:
        return False
    _glaetten_rufe.append(jetzt)
    return True


@app.post("/api/glaetten", dependencies=[Depends(require_auth)])
async def glaetten(body: Diktat) -> dict:
    """Einen diktierten Text aufräumen — auf Knopfdruck, vor dem Absenden."""
    text = body.text.strip()
    if not text:
        return {"text": ""}

    if not _glaetten_erlaubt():
        raise HTTPException(429, "Zu viele Glätt-Anfragen kurz hintereinander — kurz warten.")

    try:
        sauber = await asyncio.to_thread(_glaetten, text)
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Das Glätten hat zu lange gedauert — versuch es nochmal.")
    except RuntimeError:
        raise HTTPException(502, "Das Glätten hat gerade nicht geklappt.")

    # Kommt nichts Brauchbares zurück, lieber den Urtext behalten als eine leere
    # Zeile — nichts geht verloren.
    return {"text": sauber or text}


@app.post("/api/sessions/{name}/senden", dependencies=[Depends(require_auth)])
async def session_senden(name: str, body: Nachricht) -> dict:
    """Eine Nachricht an Claude — aus der Lese-Ansicht, ohne Terminal.

    Im Terminal tippt man direkt; hier gibt es keine offene Verbindung, also
    reichen wir den Text über tmux hinein, als hätte ihn jemand getippt.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    # Seit dem Stückel-Fix gibt es keine technische Grenze mehr — also eine
    # vernünftige: 2 Millionen Zeichen sind ein sehr dickes Buch. Alles darüber
    # ist ein Versehen (oder Missbrauch) und würde die kleine Maschine würgen.
    if len(body.text) > 2_000_000:
        raise HTTPException(413, "Die Nachricht ist zu groß (mehr als 2 Millionen Zeichen).")

    # Bevor wir tippen: Liegt ein Auswahl-Dialog über der Eingabe? Dann würde
    # der Text im Dialog versickern statt bei Claude anzukommen — so hat der
    # Brain-Chat am 17.08. Nachrichten verschluckt. Bietet der Dialog selbst
    # Escape als Ausweg an, drücken wir ihn weg; wenn nicht, lieber ein
    # ehrlicher Fehler als eine stumm verlorene Nachricht.
    zustand = await asyncio.to_thread(tmux.dialog_zustand, name)
    if zustand == "abbrechbar":
        tmux.send_key(name, "Escape")
        await asyncio.sleep(0.8)
        zustand = await asyncio.to_thread(tmux.dialog_zustand, name)
    if zustand != "frei":
        raise HTTPException(
            409,
            "Claude zeigt in dieser Sitzung gerade eine Frage an, die sich "
            "nicht von selbst schließen lässt. Bitte einmal das Terminal "
            "öffnen und sie beantworten — sonst würde die Nachricht "
            "verschluckt.",
        )

    tmux.send_text(name, body.text)
    # Kurz Luft lassen: Text und Enter im selben Atemzug verschluckt Claude
    # Code gelegentlich.
    await asyncio.sleep(0.3)
    tmux.send_key(name, "Enter")
    return {"ok": True}


# --- Das Terminal ------------------------------------------------------------

@app.websocket("/ws/{name}")
async def terminal(
    websocket: WebSocket,
    name: str,
    cols: int = Query(80),
    rows: int = Query(24),
) -> None:
    if not geraete.anmeldung_gueltig(websocket.cookies.get(COOKIE, "")):
        await websocket.close(code=1008, reason="Nicht angemeldet.")
        return

    if not tmux.exists(name):
        await websocket.close(code=1008, reason="Diese Sitzung gibt es nicht.")
        return

    await websocket.accept()
    process = await tmux.attach(name, cols, rows)

    async def server_to_browser() -> None:
        """Was das Terminal ausgibt, geht ans Handy."""
        while True:
            chunk = await process.stdout.read(4096)
            if not chunk:
                break
            await websocket.send_bytes(chunk)

    async def browser_to_server() -> None:
        """Was du tippst, geht ins Terminal."""
        while True:
            message = await websocket.receive()

            if "bytes" in message and message["bytes"] is not None:
                process.stdin.write(message["bytes"])
                await process.stdin.drain()

            elif "text" in message and message["text"] is not None:
                text = message["text"]
                # Eine Größenänderung kommt als "\x00resize:80:24" herein,
                # damit sie sich nicht mit echten Tastendrücken vermischt.
                if text.startswith("\x00resize:"):
                    _, new_cols, new_rows = text[8:].split(":")
                    tmux.resize(name, int(new_cols), int(new_rows))
                else:
                    process.stdin.write(text.encode())
                    await process.stdin.drain()

    pump = [
        asyncio.create_task(server_to_browser()),
        asyncio.create_task(browser_to_server()),
    ]
    try:
        # Sobald eine Richtung abbricht, ist die Verbindung zu Ende.
        await asyncio.wait(pump, return_when=asyncio.FIRST_COMPLETED)
    except WebSocketDisconnect:
        pass
    finally:
        for task in pump:
            task.cancel()
        # Nur den Zuschauer beenden, nicht die Sitzung selbst — die läuft
        # weiter, auch wenn du das Handy weglegst. Das ist der ganze Punkt.
        if process.returncode is None:
            process.terminate()
            await process.wait()


# --- Die Oberfläche ----------------------------------------------------------

@app.get("/")
def index() -> Response:
    """Die Startseite — mit der Versionsnummer des Servers hineingeschrieben.

    Hier, und nur hier, entscheidet sich, welche Fassung im Handy läuft. Der
    Server trägt seine Version in die Seite ein; Stil und Logik hängen mit
    dieser Nummer im Namen daran. Und er verbietet dem Browser, die Seite
    aufzubewahren — so holt das Handy sie bei jedem Öffnen frisch und bekommt
    damit zwangsläufig die passenden Dateien. Früher stand die Nummer ein
    zweites Mal fest im Handy-Code; lief sie mit dem Server auseinander, warf
    sich die App in eine Neulade-Schleife und man flog heraus. Diese zweite
    Nummer gibt es nicht mehr.
    """
    return _index_html()


def _index_html() -> Response:
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("__VERSION__", str(VERSION))
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/teilen")
def teilen_ziel() -> Response:
    """Landeplatz für den Teilen-Knopf anderer Apps ("share_target" im Manifest).

    Dieselbe Seite wie "/" — was geteilt wurde, holt sich app.js selbst, sobald
    die Anmeldung steht (siehe teilenAusfuehren()).
    """
    return _index_html()


@app.post("/teilen")
def teilen_ziel_post() -> Response:
    """Notausgang, falls der Service Worker das Geteilte nicht abfängt.

    Im Normalfall kommt hier nichts an: Android schickt Geteiltes als POST an
    diese Adresse, und der Service Worker greift es vorher ab, weil nur er
    Dateien entgegennehmen kann. Steht er noch nicht (frisch eingerichtet, kurz
    nach einer Aktualisierung), landet das Formular beim Server. Dann geht die
    App wenigstens auf, statt dem Nutzer einen Fehler zu zeigen — den Inhalt
    bekommt sie so allerdings nicht, der muss nochmal geteilt werden.

    303 statt 307: Der Browser soll die Seite danach mit GET holen, sonst
    schickt ein Neuladen das Formular ein zweites Mal.
    """
    return Response(status_code=303, headers={"Location": "/teilen"})


app.mount("/", StaticFiles(directory=WEB_DIR), name="web")


def main() -> None:
    import uvicorn

    # Kein Zugangswort mehr, das gesetzt sein müsste. Sind keine Geräte
    # freigeschaltet, kommt schlicht niemand herein — der Dienst ist dann zu,
    # nicht offen. Das ist der sichere Ausgangszustand.
    if not geraete.liste():
        print(
            "Noch kein Gerät freigeschaltet — es kommt niemand herein.\n"
            "Öffne die App am Handy, sie zeigt dir deinen Geräteschlüssel.\n"
            "Dann:  ./scripts/geraet-erlauben.sh handy <schlüssel>"
        )

    uvicorn.run(
        app,
        host=os.environ.get("HETZNER_APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("HETZNER_APP_PORT", "8787")),
    )


if __name__ == "__main__":
    main()
