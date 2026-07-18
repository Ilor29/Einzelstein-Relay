"""Der Dienst, der auf dem Hetzner läuft.

Er tut drei Dinge:
  1. Sitzungen verwalten (auflisten, starten, beenden, anheften)
  2. Ein Terminal ans Handy durchreichen (über WebSocket)
  3. Text vorlesen (über Piper)
"""

from __future__ import annotations

import asyncio
import os
import secrets
import shutil
import subprocess
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

from . import bibliothek, geraete, melden, mitschrift, state, tmux, tts, verlauf

WEB_DIR = Path(__file__).parent.parent / "web"

COOKIE = "hetzner_app_anmeldung"

app = FastAPI(title="Hetzner-App")


@app.middleware("http")
async def sicherheits_header(request: Request, call_next):
    """Ein paar schützende Kopfzeilen auf jede Antwort.

    Bewusst OHNE Content-Security-Policy: Eine falsch gesetzte CSP legt die App
    lahm (Inline-Skript/-Stil, WebSocket, Audio-Blobs) und gehört erst nach
    einem echten Test im Browser gesetzt — dann am besten in Caddy. Diese drei
    Header dagegen brechen nichts und kosten nichts.
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
    return antwort


# Anhänge — Fotos und Dokumente — sind Durchgangsware: einmal an Claude gereicht,
# liegen sie nur noch als Altlast im Projekt. Diese Ordner räumen wir darum von
# selbst; sie stehen bewusst außerhalb von Git (siehe die .gitignore beim Upload).
ANHANG_ORDNER = (".hetzner-bilder", ".hetzner-dateien")

# Wie lange ein Anhang liegen bleiben darf. Ein paar Tage, damit man einen
# Screenshot von gestern noch nachreichen oder ansehen kann — aber nicht ewig.
ANHANG_HALTBAR_TAGE = 3


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


@app.on_event("startup")
async def waechter_starten() -> None:
    """Der Wächter behält die Sitzungen im Auge und meldet sich, wenn eine
    fertig ist oder eine Rückfrage hat."""
    asyncio.create_task(melden.waechter())

    # Die Stimme schon mal in den Speicher holen. Sonst wartet man beim ersten
    # Vorlesen drei Sekunden auf ein Modell, das man auch vorher hätte laden
    # können.
    asyncio.create_task(asyncio.to_thread(tts.vorladen))

    # Alte Anhänge (Fotos, Dokumente) von selbst wegräumen.
    asyncio.create_task(anhaenge_aufraeumen())


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
VERSION = 78


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

    try:
        tmux.create(name, str(cwd), ohne_rueckfragen=body.ohne_rueckfragen)
    except tmux.TmuxError as error:
        raise HTTPException(409, str(error))

    state.update(
        name,
        pinned=body.pinned,
        notify_when_done=body.notify_when_done,
        created_prompt=body.first_prompt,
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
    tmux.send_text(name, prompt)
    # Kurz Luft lassen: Text und Enter im selben Atemzug verschluckt Claude
    # Code gelegentlich.
    await asyncio.sleep(0.5)
    tmux.send_key(name, "Enter")


@app.patch("/api/sessions/{name}", dependencies=[Depends(require_auth)])
def patch_session(name: str, body: Patch) -> dict:
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    changes = {}
    if body.pinned is not None:
        changes["pinned"] = body.pinned
    if body.notify_when_done is not None:
        changes["notify_when_done"] = body.notify_when_done
    if body.anzeige is not None:
        # Ein leerer Name heißt: zurück zum technischen Namen.
        changes["anzeige"] = body.anzeige.strip()[:60]

    meta = state.update(name, **changes)
    return {
        "ok": True,
        "pinned": meta.pinned,
        "notifyWhenDone": meta.notify_when_done,
        "anzeige": meta.anzeige,
    }


@app.delete("/api/sessions/{name}", dependencies=[Depends(require_auth)])
def delete_session(name: str) -> dict:
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    # Fremde Sitzungen — etwa die, in der Claude Code selbst läuft — darf man
    # ansehen und bedienen, aber nicht abschießen. Sonst legt man sich mit
    # einem Fingertipp die eigene Arbeitsumgebung lahm.
    if not treffer[0].eigen:
        raise HTTPException(403, "Diese Sitzung gehört nicht der App — sie bleibt.")

    tmux.kill(name)
    state.forget(name)
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


@app.get("/api/sessions/{name}/text", dependencies=[Depends(require_auth)])
def session_text(name: str) -> dict:
    """Claudes letzte Antwort, zum Vorlesen."""
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    # Aus der Mitschrift, nicht vom Bildschirm: Dort steht die Antwort ganz,
    # nicht nur der Teil, der gerade zu sehen ist. Sie steht dort als Markdown —
    # ungefiltert vorgelesen wird daraus Kauderwelsch aus Sternchen und Rauten.
    for block in reversed(mitschrift.lesen(treffer[0].cwd)):
        if block["typ"] == "claude" and block["text"].strip():
            gesprochen = tts.fuer_stimme(block["text"])
            if gesprochen:
                return {"text": gesprochen}

    # Keine Mitschrift? Dann eben doch vom Bildschirm.
    return {"text": tts.for_speech(tmux.capture(name, lines=200))}


@app.get("/api/sessions/{name}/verlauf", dependencies=[Depends(require_auth)])
def session_verlauf(name: str) -> list[dict]:
    """Die Unterhaltung dieses Projekts — alle Gespräche in einer Zeitleiste.

    Nicht vom Terminal-Bildschirm abgelesen und geraten: Claude Code schreibt
    jede Sitzung ohnehin mit, vollständig und sauber getrennt nach Sprecher.
    Und nicht ein Verlauf je Terminal, sondern einer je Projekt — ob am
    Rechner, per Fernsteuerung oder hier gesprochen wurde, ist dieselbe Arbeit
    am selben Ordner.
    """
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    bloecke = mitschrift.lesen(treffer[0].cwd)

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
DOK_ENDUNGEN = {
    ".pdf", ".md", ".markdown", ".txt", ".text", ".rtf",
    ".doc", ".docx", ".odt", ".csv", ".tsv",
    ".xls", ".xlsx", ".ods", ".ppt", ".pptx",
    ".json", ".yaml", ".yml", ".log", ".xml", ".html",
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
            "Markdown, Text, Tabellen und ähnliche Dokumente.",
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
MODELLE = {
    "fable": ("Fable 5", "das neueste"),
    "opus": ("Opus 4.8", "am stärksten, verbraucht die Limits schneller"),
    "sonnet": ("Sonnet 5", "am effizientesten für Alltagsaufgaben"),
    "haiku": ("Haiku 4.5", "am schnellsten für kurze Antworten"),
}


@app.get("/api/modelle", dependencies=[Depends(require_auth)])
def modelle() -> list[dict]:
    return [
        {"name": name, "anzeige": anzeige, "art": art}
        for name, (anzeige, art) in MODELLE.items()
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

    state.update(name, modell=body.name)
    return {"ok": True, "modell": body.name}


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
    """Hängt die Sitzung gerade an einer Rückfrage? Dann hier, mit Antworten."""
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    return state.frage(name) or {}


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
        return subprocess.run(
            ["git", "-C", str(ordner),
             "-c", "user.name=Hetzner-App",
             "-c", "user.email=hetzner-app@localhost", *args],
            capture_output=True, text=True,
        )

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
    html = (WEB_DIR / "index.html").read_text(encoding="utf-8")
    html = html.replace("__VERSION__", str(VERSION))
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


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
