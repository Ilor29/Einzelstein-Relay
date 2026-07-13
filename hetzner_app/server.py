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
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import state, tmux, tts

WEB_DIR = Path(__file__).parent.parent / "web"

# Ohne Zugangswort läuft der Dienst nicht. Eine Shell auf dem Server darf
# nicht offen im Netz stehen — auch nicht "nur kurz zum Ausprobieren".
TOKEN = os.environ.get("HETZNER_APP_TOKEN", "")

COOKIE = "hetzner_app_token"

app = FastAPI(title="Hetzner-App")


# --- Zugangsschutz -----------------------------------------------------------

def _token_ok(supplied: str) -> bool:
    # Zeitkonstanter Vergleich, damit man das Zugangswort nicht Zeichen für
    # Zeichen erraten kann.
    return bool(supplied) and secrets.compare_digest(supplied, TOKEN)


def require_auth(request: Request) -> None:
    supplied = (
        request.headers.get("x-token")
        or request.cookies.get(COOKIE)
        or ""
    )
    if not _token_ok(supplied):
        raise HTTPException(status_code=401, detail="Nicht angemeldet.")


class Login(BaseModel):
    token: str


@app.post("/api/login")
def login(body: Login) -> Response:
    if not _token_ok(body.token):
        raise HTTPException(status_code=401, detail="Falsches Zugangswort.")
    response = JSONResponse({"ok": True})
    response.set_cookie(
        COOKIE, body.token,
        httponly=True,
        samesite="strict",
        secure=True,       # nur über HTTPS — siehe Caddy-Konfiguration
        max_age=60 * 60 * 24 * 365,
    )
    return response


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
        # Erst tippen, wenn Claude Code auch zuhört. Sonst landet der Auftrag
        # im Nichts und die Sitzung steht leer da.
        bereit = await asyncio.to_thread(tmux.warte_bis_bereit, body.name, 30)
        if bereit:
            tmux.send_text(body.name, body.first_prompt)
            # Kurz Luft lassen: Text und Enter im selben Atemzug verschluckt
            # Claude Code gelegentlich.
            await asyncio.sleep(0.5)
            tmux.send_key(body.name, "Enter")

    return {"ok": True, "name": body.name}


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
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
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


# --- Vorlesen ----------------------------------------------------------------

class Speak(BaseModel):
    text: str


@app.post("/api/speak", dependencies=[Depends(require_auth)])
async def speak(body: Speak) -> Response:
    audio = await tts.synthesize(body.text)
    return Response(content=audio, media_type="audio/wav")


@app.get("/api/sessions/{name}/text", dependencies=[Depends(require_auth)])
def session_text(name: str) -> dict:
    """Der Text der Sitzung, aufbereitet zum Vorlesen."""
    if not tmux.exists(name):
        raise HTTPException(404, "Diese Sitzung gibt es nicht.")
    screen = tmux.capture(name, lines=200)
    return {"text": tts.for_speech(screen)}


# --- Das Terminal ------------------------------------------------------------

@app.websocket("/ws/{name}")
async def terminal(
    websocket: WebSocket,
    name: str,
    cols: int = Query(80),
    rows: int = Query(24),
) -> None:
    supplied = websocket.cookies.get(COOKIE, "")
    if not _token_ok(supplied):
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

    if not TOKEN:
        raise SystemExit(
            "HETZNER_APP_TOKEN ist nicht gesetzt.\n"
            "Ohne Zugangswort startet der Dienst nicht — sonst hätte jeder, "
            "der die Adresse kennt, eine Shell auf deinem Server.\n\n"
            "  export HETZNER_APP_TOKEN=$(openssl rand -hex 24)"
        )

    uvicorn.run(
        app,
        host=os.environ.get("HETZNER_APP_HOST", "127.0.0.1"),
        port=int(os.environ.get("HETZNER_APP_PORT", "8787")),
    )


if __name__ == "__main__":
    main()
