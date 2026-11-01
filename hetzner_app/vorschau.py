"""Vorschau neben dem Chat (Monitor-Baustein 7): welche Seiten im eigenen Webspace liegen.

Nur lesen. Der Webspace ist der Ordner (Vorgabe ~/seiten), den ein eigener Dienst unter
`HETZNER_APP_VORSCHAU_BASIS` ausliefert. Ist die Basis nicht gesetzt, gibt es keine
Vorschau (Lea und Lorenz haben ihre eigene Adresse und ihren eigenen Ordner).
"""
from __future__ import annotations

import html
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

MAX_EINTRAEGE = 60


def basis() -> str:
    """Die Adresse des Webspace ohne Schrägstrich am Ende, oder leer."""
    roh = os.environ.get("HETZNER_APP_VORSCHAU_BASIS", "").strip().rstrip("/")
    t = urlsplit(roh)
    return roh if t.scheme == "https" and t.netloc and not t.path.strip("/") else ""


def herkunft() -> str:
    """Nur Schema und Rechner, für die Content-Security-Policy (frame-src)."""
    t = urlsplit(basis())
    return f"{t.scheme}://{t.netloc}" if t.netloc else ""


def _ordner() -> Path:
    return Path(os.environ.get("HETZNER_APP_VORSCHAU_ORDNER", Path.home() / "seiten"))


def _titel(index: Path, name: str) -> str:
    try:
        kopf = index.read_text(encoding="utf-8", errors="replace")[:4000]
        m = re.search(r"<title[^>]*>(.*?)</title>", kopf, re.S | re.I)
        if m:
            return html.unescape(" ".join(m.group(1).split()))[:120] or name
    except OSError:
        pass
    return name


def uebersicht() -> dict:
    b = basis()
    if not b:
        return {"aktiv": False, "basis": "", "seiten": []}
    wurzel = _ordner()
    seiten = []
    try:
        for d in wurzel.iterdir():
            if d.name.startswith((".", "_")) or not d.is_dir():
                continue
            index = d / "index.html"
            if not index.is_file():
                continue
            seiten.append((index.stat().st_mtime, d.name, _titel(index, d.name)))
    except OSError:
        return {"aktiv": True, "basis": b, "seiten": []}
    seiten.sort(reverse=True)
    return {
        "aktiv": True,
        "basis": b,
        "seiten": [{"name": n, "titel": t, "geaendert": int(m)} for m, n, t in seiten[:MAX_EINTRAEGE]],
    }
