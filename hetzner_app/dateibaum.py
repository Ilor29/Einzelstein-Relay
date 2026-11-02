"""Dateibaum der Karte: Ordner und Dateien im Arbeitsordner einer Karte, nur zum Lesen.

Bauplan Monitor-Ansicht, Baustein 8. Alles bleibt unter dem Arbeitsordner der
Karte (echter Pfad, Verknüpfungen nach draußen werden nicht gefolgt). Ordner mit
Zugangsdaten und Zwischenspeicher werden gar nicht aufgelistet. Dateien mit
Zugangsdaten erscheinen nur mit Namen, ihr Inhalt wird nie ausgeliefert.
"""
from __future__ import annotations

import os

from .aenderungen import geheim

_MAX_EINTRAEGE = 400
_MAX_BYTES = 200_000

# Ordner, die nie erscheinen: Zugangsdaten, Zwischenspeicher, Abhängigkeiten.
_VERSTECKT = {
    ".git", ".ssh", ".gnupg", ".aws", ".claude", ".hetzner-app", ".config", ".cache",
    ".local", ".npm", "node_modules", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", ".hetzner-bilder",
}


def _innen(ordner: str, rel: str) -> str | None:
    """Echter Pfad von ordner/rel, wenn er unter ordner bleibt, sonst None."""
    if not ordner or not os.path.isdir(ordner):
        return None
    wurzel = os.path.realpath(ordner)
    ziel = os.path.realpath(os.path.join(wurzel, rel.lstrip("/")))
    if ziel != wurzel and not ziel.startswith(wurzel + os.sep):
        return None
    teile = os.path.relpath(ziel, wurzel).split(os.sep)
    if any(t in _VERSTECKT for t in teile):
        return None
    return ziel


def liste(ordner: str, rel: str = "") -> dict:
    ziel = _innen(ordner, rel)
    if not ziel or not os.path.isdir(ziel):
        return {"ok": False, "eintraege": []}
    eintraege = []
    try:
        with os.scandir(ziel) as it:
            for e in it:
                if e.name in _VERSTECKT:
                    continue
                try:
                    ist_ordner = e.is_dir(follow_symlinks=False)
                    if e.is_symlink():
                        echt = os.path.realpath(e.path)
                        wurzel = os.path.realpath(ordner)
                        if not (echt == wurzel or echt.startswith(wurzel + os.sep)):
                            continue
                        ist_ordner = os.path.isdir(echt)
                    groesse = 0 if ist_ordner else e.stat().st_size
                except OSError:
                    continue
                eintraege.append({
                    "name": e.name, "ordner": ist_ordner, "groesse": groesse,
                    "geheim": (not ist_ordner) and geheim(e.name),
                })
    except OSError:
        return {"ok": False, "eintraege": []}
    eintraege.sort(key=lambda x: (not x["ordner"], x["name"].lower()))
    gekuerzt = len(eintraege) > _MAX_EINTRAEGE
    return {"ok": True, "eintraege": eintraege[:_MAX_EINTRAEGE], "gekuerzt": gekuerzt}


def lesen(ordner: str, rel: str) -> dict:
    ziel = _innen(ordner, rel)
    if not ziel or not os.path.isfile(ziel):
        return {"ok": False, "grund": "nicht gefunden"}
    name = os.path.basename(ziel)
    if geheim(name) or geheim(rel):
        return {"ok": True, "geheim": True, "name": name, "text": ""}
    try:
        groesse = os.path.getsize(ziel)
        with open(ziel, "rb") as f:
            roh = f.read(_MAX_BYTES)
    except OSError:
        return {"ok": False, "grund": "nicht lesbar"}
    if b"\0" in roh[:4096]:
        return {"ok": True, "binaer": True, "name": name, "groesse": groesse, "text": ""}
    return {
        "ok": True, "name": name, "groesse": groesse,
        "gekuerzt": groesse > _MAX_BYTES,
        "text": roh.decode("utf-8", "replace"),
    }
