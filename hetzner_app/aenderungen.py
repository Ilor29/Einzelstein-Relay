"""Änderungen der Karte: was im Ordner einer Karte gegenüber dem letzten Commit anders ist.

Nur lesend. Quelle ist Git im Kartenordner (git diff gegen HEAD plus neue,
noch nicht erfasste Dateien). Steht der Ordner nicht unter Git, kommt
„git": false zurück und die App zeigt nichts.

Dateien mit Zugangsdaten (.env, Schlüssel und ähnliche) erscheinen nur mit
Namen, ihr Inhalt wird nie ausgeliefert (Bauplan Monitor-Ansicht, Baustein 8).
"""
from __future__ import annotations

import os
import re
import subprocess

_GIT_ENV = {**os.environ, "GIT_OPTIONAL_LOCKS": "0", "LC_ALL": "C.UTF-8"}
_MAX_DATEIEN = 200
_MAX_ZEILEN = 400
_MAX_BYTES = 200_000

# Dateinamen, deren Inhalt nie angezeigt wird.
_GEHEIM = re.compile(
    r"(^|/)(\.env[^/]*|.*\.(pem|key|p12|pfx|kdbx)|id_(rsa|ed25519|ecdsa)[^/]*|"
    r"umgebung|.*secret.*|.*passw.*|.*token.*|.*credential.*|\.netrc)$",
    re.I,
)


def _git(ordner: str, *args: str, timeout: int = 8) -> subprocess.CompletedProcess | None:
    try:
        return subprocess.run(
            ["git", "-c", "core.quotepath=false", "-C", ordner, *args],
            capture_output=True, text=True, timeout=timeout, env=_GIT_ENV,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def geheim(pfad: str) -> bool:
    return bool(_GEHEIM.search(pfad))


def uebersicht(ordner: str) -> dict:
    """Je Datei Plus und Minus, dazu die Summen."""
    if not ordner or not os.path.isdir(ordner):
        return {"git": False}
    r = _git(ordner, "rev-parse", "--is-inside-work-tree")
    if not r or r.returncode != 0 or r.stdout.strip() != "true":
        return {"git": False}

    dateien: dict[str, dict] = {}
    hat_kopf = _git(ordner, "rev-parse", "--verify", "-q", "HEAD")
    basis = ["HEAD"] if hat_kopf and hat_kopf.returncode == 0 else []
    d = _git(ordner, "diff", "--numstat", "--no-ext-diff", *basis)
    if d and d.returncode == 0:
        for zeile in d.stdout.splitlines():
            teile = zeile.split("\t", 2)
            if len(teile) != 3:
                continue
            plus, minus, pfad = teile
            if " => " in pfad:           # umbenannt: Anzeige „alt => neu“ nicht auflösen
                pfad = pfad.split(" => ")[-1].replace("}", "").replace("{", "")
            binaer = plus == "-"
            dateien[pfad] = {
                "pfad": pfad,
                "plus": 0 if binaer else int(plus),
                "minus": 0 if binaer else int(minus),
                "neu": False, "binaer": binaer,
            }
    n = _git(ordner, "ls-files", "--others", "--exclude-standard")
    if n and n.returncode == 0:
        for pfad in n.stdout.splitlines():
            if pfad in dateien or not pfad:
                continue
            voll = os.path.join(ordner, pfad)
            zeilen = 0
            binaer = False
            try:
                if os.path.getsize(voll) > _MAX_BYTES:
                    binaer = True
                elif not geheim(pfad):
                    with open(voll, "rb") as f:
                        roh = f.read()
                    binaer = b"\0" in roh
                    zeilen = 0 if binaer else roh.count(b"\n") + (0 if roh.endswith(b"\n") or not roh else 1)
            except OSError:
                continue
            dateien[pfad] = {"pfad": pfad, "plus": zeilen, "minus": 0, "neu": True, "binaer": binaer}

    liste = sorted(dateien.values(), key=lambda x: -(x["plus"] + x["minus"]))
    gekuerzt = len(liste) > _MAX_DATEIEN
    liste = liste[:_MAX_DATEIEN]
    for x in liste:
        x["geheim"] = geheim(x["pfad"])
    return {
        "git": True,
        "dateien": liste,
        "plus": sum(x["plus"] for x in liste),
        "minus": sum(x["minus"] for x in liste),
        "gekuerzt": gekuerzt,
    }


def datei_diff(ordner: str, pfad: str) -> dict:
    """Die Zeilen einer einzelnen geänderten Datei. Nur Pfade aus der Übersicht."""
    uebers = uebersicht(ordner)
    if not uebers.get("git"):
        return {"fehler": "Kein Git-Ordner."}
    eintrag = next((x for x in uebers["dateien"] if x["pfad"] == pfad), None)
    if not eintrag:
        return {"fehler": "Diese Datei ist nicht geändert."}
    if eintrag["geheim"]:
        return {"geheim": True, "zeilen": []}
    if eintrag["binaer"]:
        return {"binaer": True, "zeilen": []}

    if eintrag["neu"]:
        try:
            with open(os.path.join(ordner, pfad), encoding="utf-8", errors="replace") as f:
                text = f.read(_MAX_BYTES)
        except OSError:
            return {"fehler": "Nicht lesbar."}
        zeilen = ["+" + z for z in text.splitlines()]
    else:
        hat_kopf = _git(ordner, "rev-parse", "--verify", "-q", "HEAD")
        basis = ["HEAD"] if hat_kopf and hat_kopf.returncode == 0 else []
        d = _git(ordner, "diff", "--no-ext-diff", "--no-color", "-U2", *basis, "--", pfad)
        if not d or d.returncode != 0:
            return {"fehler": "Git konnte den Unterschied nicht liefern."}
        zeilen = [z for z in d.stdout.splitlines() if not z.startswith(("diff ", "index ", "--- ", "+++ "))]
    gekuerzt = len(zeilen) > _MAX_ZEILEN
    return {"zeilen": zeilen[:_MAX_ZEILEN], "gekuerzt": gekuerzt}
