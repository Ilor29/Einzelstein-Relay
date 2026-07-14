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
import time
from pathlib import Path

from fastapi import (
    Depends, FastAPI, File, HTTPException, Query, Request, UploadFile,
    WebSocket, WebSocketDisconnect,
)
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import geraete, melden, mitschrift, state, tmux, tts, verlauf

WEB_DIR = Path(__file__).parent.parent / "web"

COOKIE = "hetzner_app_anmeldung"

app = FastAPI(title="Hetzner-App")


@app.on_event("startup")
async def waechter_starten() -> None:
    """Der Wächter behält die Sitzungen im Auge und meldet sich, wenn eine
    fertig ist oder eine Rückfrage hat."""
    asyncio.create_task(melden.waechter())


# --- Zugangsschutz -----------------------------------------------------------

def require_auth(request: Request) -> None:
    if not geraete.anmeldung_gueltig(request.cookies.get(COOKIE, "")):
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")


class Unterschrift(BaseModel):
    aufgabe: str
    unterschrift: str


# Hochzählen, sobald sich an der Oberfläche etwas ändert. Die App prüft das
# beim Start und lädt sich selbst neu, wenn sie veraltet ist — sonst läuft man
# stundenlang gegen einen Fehler an, der längst behoben ist.
VERSION = 15


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
        COOKIE, geraete.anmeldung_ausstellen(),
        httponly=True,
        samesite="strict",
        secure=True,        # nur über HTTPS — siehe Caddy-Konfiguration
        max_age=geraete.ANMELDUNG_GILT,
    )
    return antwort


@app.get("/api/geraete", dependencies=[Depends(require_auth)])
def geraete_liste() -> list[dict]:
    return [{"name": g.name, "hinzugefuegt": g.hinzugefuegt} for g in geraete.liste()]


# --- Sitzungen ---------------------------------------------------------------

class NewSession(BaseModel):
    name: str = Field(min_length=1, max_length=60, pattern=r"^[A-Za-z0-9._-]+$")
    cwd: str
    first_prompt: str = ""
    pinned: bool = False
    notify_when_done: bool = False


class Patch(BaseModel):
    pinned: bool | None = None
    notify_when_done: bool | None = None


@app.get("/api/sessions", dependencies=[Depends(require_auth)])
def list_sessions() -> list[dict]:
    return state.overview()


@app.post("/api/sessions", dependencies=[Depends(require_auth)])
async def create_session(body: NewSession) -> dict:
    cwd = Path(body.cwd).expanduser()
    if not cwd.is_dir():
        raise HTTPException(400, f"Den Ordner {body.cwd} gibt es nicht.")

    try:
        tmux.create(body.name, str(cwd))
    except tmux.TmuxError as error:
        raise HTTPException(409, str(error))

    state.update(
        body.name,
        pinned=body.pinned,
        notify_when_done=body.notify_when_done,
        created_prompt=body.first_prompt,
    )

    if body.first_prompt:
        # Der erste Auftrag darf nicht auf die Antwort warten lassen. Claude
        # Code braucht ein paar Sekunden, bis es Eingaben annimmt — solange
        # dürfen wir das Handy nicht hängen lassen. Also: Sitzung sofort
        # melden, Auftrag im Hintergrund nachschieben.
        asyncio.create_task(_ersten_auftrag_schicken(body.name, body.first_prompt))

    return {"ok": True, "name": body.name}


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

    meta = state.update(name, **changes)
    return {"ok": True, "pinned": meta.pinned, "notifyWhenDone": meta.notify_when_done}


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


@app.post("/api/melden/eintragen", dependencies=[Depends(require_auth)])
async def melden_eintragen(anmeldung: dict) -> dict:
    melden.eintragen(anmeldung)
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


@app.post("/api/speak", dependencies=[Depends(require_auth)])
async def speak(body: Speak) -> Response:
    audio = await tts.synthesize(body.text)
    return Response(content=audio, media_type="audio/wav")


@app.get("/api/sessions/{name}/text", dependencies=[Depends(require_auth)])
def session_text(name: str) -> dict:
    """Claudes letzte Antwort, zum Vorlesen."""
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    # Aus der Mitschrift, nicht vom Bildschirm: Dort steht die Antwort ganz,
    # nicht nur der Teil, der gerade zu sehen ist.
    bloecke = mitschrift.lesen(treffer[0].cwd)
    for block in reversed(bloecke):
        if block["typ"] == "claude" and block["text"].strip():
            return {"text": block["text"]}

    # Keine Mitschrift? Dann eben doch vom Bildschirm.
    return {"text": tts.for_speech(tmux.capture(name, lines=200))}


@app.get("/api/sessions/{name}/verlauf", dependencies=[Depends(require_auth)])
def session_verlauf(name: str) -> list[dict]:
    """Die Unterhaltung, so wie sie wirklich stattfand.

    Nicht mehr vom Terminal-Bildschirm abgelesen und geraten: Claude Code
    schreibt jede Sitzung ohnehin mit, vollständig und sauber getrennt nach
    Sprecher. Das ist die richtige Quelle. Sie überlebt jeden Neustart, reicht
    beliebig weit zurück, und niemand verwechselt mehr, wer was gesagt hat.
    """
    treffer = [s for s in tmux.list_sessions() if s.name == name]
    if not treffer:
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

    bloecke = mitschrift.lesen(treffer[0].cwd)

    # Findet sich keine Mitschrift — etwa bei einer ganz frischen Sitzung —,
    # lesen wir notfalls doch den Bildschirm ab. Besser als eine leere Seite.
    if not bloecke:
        return verlauf.lesen(tmux.capture(name, lines=5000))

    return bloecke


BILDER = Path.home() / ".hetzner-app" / "bilder"

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


@app.post("/api/sessions/{name}/senden", dependencies=[Depends(require_auth)])
async def session_senden(name: str, body: Nachricht) -> dict:
    """Eine Nachricht an Claude — aus der Lese-Ansicht, ohne Terminal.

    Im Terminal tippt man direkt; hier gibt es keine offene Verbindung, also
    reichen wir den Text über tmux hinein, als hätte ihn jemand getippt.
    """
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")

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
def index() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


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
