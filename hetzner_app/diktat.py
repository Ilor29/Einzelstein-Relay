"""Eigenes Diktat (Whisper auf diesem Server) als zweite Wahl neben dem
Google-Diktat des Browsers. Roli 31.10.2026 „10. Ja“ (gegen Aussetzer und
Verhörer), „22. Ja“ (Modell small, Wortschatz als Hinweis).

Das Handy nimmt auf und schickt die Aufnahme; hier wird sie mit ffmpeg auf
16 kHz Mono gebracht und an den Arbeiter (whisper_worker.py) gegeben. Der
Arbeiter läuft im Python aus ~/werkzeuge/whisper/.venv. Fehlt das (Lea,
Lorenz), ist das Diktat „nicht verfügbar“ und die App blendet die Wahl aus."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
import threading
from pathlib import Path

WHISPER_PYTHON = Path.home() / "werkzeuge" / "whisper" / ".venv" / "bin" / "python"
ARBEITER = Path(__file__).with_name("whisper_worker.py")
AUSSPRACHE_DATEI = Path.home() / "projekte" / "Kaira-Assistent" / "server" / "aussprache.txt"
MAX_BYTES = 8 * 1024 * 1024
MAX_SEKUNDEN = 180

# Immer dabei, auch wenn die Aussprache-Liste fehlt.
GRUNDWORTE = ["Claude", "Claude Code", "Relay", "GitHub", "Commit", "Kaira", "Whisper",
              "Piper", "tmux", "Playwright", "Hetzner", "Baubuch", "Brain", "Skillkontor"]

_sperre = threading.Lock()
_arbeiter: subprocess.Popen | None = None


class DiktatFehler(Exception):
    pass


def verfuegbar() -> bool:
    return WHISPER_PYTHON.is_file()


def hinweis() -> str:
    """Wortschatz für Whisper: die Wörter links in Kairas Aussprache-Liste
    (so schreibt man sie), dazu die Grundworte. Kurz halten, der Hinweis
    zählt gegen die Rechenzeit."""
    worte = list(GRUNDWORTE)
    try:
        for zeile in AUSSPRACHE_DATEI.read_text(encoding="utf-8").splitlines():
            zeile = zeile.strip()
            if zeile and not zeile.startswith("#") and " = " in zeile:
                w = zeile.split(" = ", 1)[0].strip()
                if w and w.lower() not in (x.lower() for x in worte):
                    worte.append(w)
    except OSError:
        pass
    return "Gespräch über Software und Programmierung: " + ", ".join(worte[:80]) + "."


def _arbeiter_holen() -> subprocess.Popen:
    global _arbeiter
    if _arbeiter is None or _arbeiter.poll() is not None:
        _arbeiter = subprocess.Popen(
            [str(WHISPER_PYTHON), "-I", str(ARBEITER)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8",
        )
    return _arbeiter


def erkennen(roh: bytes) -> str:
    """Aufnahme (webm, ogg, mp4 …) in Text verwandeln. Blockiert, also im
    Nebenläufer aufrufen."""
    if not verfuegbar():
        raise DiktatFehler("Das eigene Diktat ist auf diesem Server nicht eingerichtet.")
    if not roh or len(roh) > MAX_BYTES:
        raise DiktatFehler("Die Aufnahme ist leer oder zu groß.")
    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "ton.wav"
        lauf = subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", "pipe:0", "-t", str(MAX_SEKUNDEN),
             "-ac", "1", "-ar", "16000", str(wav)],
            input=roh, capture_output=True, timeout=60,
        )
        if lauf.returncode != 0 or not wav.is_file():
            raise DiktatFehler("Die Aufnahme ließ sich nicht lesen.")
        with _sperre:                    # eine Aufnahme nach der anderen
            for versuch in (1, 2):
                try:
                    proz = _arbeiter_holen()
                    proz.stdin.write(json.dumps({"wav": str(wav), "hinweis": hinweis()}) + "\n")
                    proz.stdin.flush()
                    zeile = proz.stdout.readline()
                    if not zeile:
                        raise BrokenPipeError()
                    antwort = json.loads(zeile)
                    break
                except (BrokenPipeError, OSError):
                    _beenden()
                    if versuch == 2:
                        raise DiktatFehler("Der Erkenner antwortet nicht.")
        if "fehler" in antwort:
            raise DiktatFehler(antwort["fehler"])
        return re.sub(r"\s+", " ", antwort["text"]).strip()


def _beenden() -> None:
    global _arbeiter
    if _arbeiter is not None:
        try:
            _arbeiter.kill()
        except OSError:
            pass
        _arbeiter = None
