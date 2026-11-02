"""Laufende Befehle einer Karte, mit Stopp.

Bauplan Monitor-Ansicht, Baustein 9. Quelle ist die Prozessliste, nicht der
Schirm der Karte: Claude Code startet jeden Shell-Befehl als `bash -c ... eval
'<Befehl>'` direkt unter seinem eigenen Prozess. Wir listen nur diese direkten
Kinder des `claude`-Prozesses der Karte. Beendet werden darf ebenfalls nur ein
solches Kind (Prüfung bei jedem Stopp neu), nie ein beliebiger Prozess.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess

from . import tmux

_BEFEHL = re.compile(r"eval '(.*)' < /dev/null", re.S)
_MAX_BEFEHL = 300


def _ps() -> dict[int, dict]:
    aus = subprocess.run(
        ["ps", "-eo", "pid=,ppid=,pgid=,etimes=,comm=,args="],
        capture_output=True, text=True, timeout=10,
    )
    tabelle: dict[int, dict] = {}
    for zeile in aus.stdout.splitlines():
        teile = zeile.split(None, 5)
        if len(teile) < 5:
            continue
        try:
            pid, ppid, pgid, sek = (int(t) for t in teile[:4])
        except ValueError:
            continue
        tabelle[pid] = {
            "pid": pid, "ppid": ppid, "pgid": pgid, "sek": sek,
            "comm": teile[4], "args": teile[5] if len(teile) > 5 else "",
        }
    return tabelle


def _pane_pids(name: str) -> list[int]:
    socket, sitzung = tmux._zerlegen(name)
    try:
        aus = tmux._run("list-panes", "-t", "=" + sitzung, "-F", "#{pane_pid}", socket=socket)
    except tmux.TmuxError:
        return []
    return [int(p) for p in aus.split() if p.isdigit()]


def _claude_pids(tabelle: dict[int, dict], wurzeln: list[int]) -> list[int]:
    """Alle `claude`-Prozesse unterhalb der Panes (nur die obersten je Zweig)."""
    kinder: dict[int, list[int]] = {}
    for p in tabelle.values():
        kinder.setdefault(p["ppid"], []).append(p["pid"])
    gefunden: list[int] = []
    stapel = list(wurzeln)
    while stapel:
        pid = stapel.pop()
        eintrag = tabelle.get(pid)
        if eintrag and eintrag["comm"] == "claude":
            gefunden.append(pid)
            continue
        stapel.extend(kinder.get(pid, []))
    return gefunden


def _befehl(args: str) -> str | None:
    m = _BEFEHL.search(args)
    if not m:
        return None
    text = m.group(1).replace("'\"'\"'", "'").strip()
    return text[:_MAX_BEFEHL]


def aufgaben(name: str) -> list[dict]:
    tabelle = _ps()
    eltern = set(_claude_pids(tabelle, _pane_pids(name)))
    aus = []
    for p in tabelle.values():
        if p["ppid"] not in eltern:
            continue
        befehl = _befehl(p["args"])
        if befehl is None:
            continue
        aus.append({"pid": p["pid"], "sekunden": p["sek"], "befehl": befehl})
    aus.sort(key=lambda a: -a["sekunden"])
    return aus


def stoppen(name: str, pid: int) -> bool:
    """Beendet einen Befehl der Karte samt seiner Unterprozesse. False, wenn er nicht (mehr) dazugehört."""
    tabelle = _ps()
    eltern = set(_claude_pids(tabelle, _pane_pids(name)))
    p = tabelle.get(pid)
    if not p or p["ppid"] not in eltern or _befehl(p["args"]) is None:
        return False
    try:
        # Jeder Befehl ist Leiter einer eigenen Prozessgruppe; so fallen auch Unterprozesse mit.
        if p["pgid"] == pid:
            os.killpg(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return True
    return True
