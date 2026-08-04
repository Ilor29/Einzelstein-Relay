"""Der Speicher-Wächter — misst, urteilt, meldet.

Die kleine Maschine hat schon zweimal Sitzungen verloren, weil der Speicher
vollief (17.07. OOM-Kill, 28.07. der Neustart danach). Beide Male hat es
niemand kommen sehen. Also schaut jetzt alle paar Minuten ein systemd-Timer
nach (`python -m hetzner_app.speicher`), macht aus den Zahlen eine Ampel und
schreibt sie nach ~/.hetzner-app/speicher.json — von dort liest sie die App
für die Anzeige. Kippt die Ampel auf Rot, gibt es genau EINE Push-Nachricht
aufs Handy; erst wenn sie wieder von Rot weg und erneut auf Rot springt, die
nächste. Wer bei Dauer-Rot dauernd klingelt, wird stummgeschaltet und hilft
dann gar nicht mehr.

Warum ein eigener Timer und nicht noch eine Schleife im App-Dienst: Wenn der
Speicher wirklich vollläuft, ist der App-Dienst selbst ein Kandidat fürs
Abgeräumtwerden — ein Wächter, der mit dem Bewachten stirbt, taugt nichts.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import os
import time
from pathlib import Path

DATEI = Path.home() / ".hetzner-app" / "speicher.json"

GRUEN, GELB, ROT = "gruen", "gelb", "rot"

# Die Schwellen, an denen das Urteil kippt. MemAvailable ist die ehrliche Zahl
# (was wirklich noch zu vergeben ist, Puffer eingerechnet) — "frei" wäre auf
# Linux immer fast null und ein Fehlalarm auf Dauer.
#
# Rot heißt: der nächste größere Claude-Start kann den OOM-Killer wecken.
# Ein Claude braucht 200-500 MB, also wird es unter 400 MB verfügbar ernst.
# Beim Swap zählt der VERBRAUCH: Ist er zu großen Teilen voll, hat der Kernel
# schon alles Faule ausgelagert und es bleibt kein Ausweichraum mehr.
ROT_VERFUEGBAR_MB = 400
ROT_SWAP_ANTEIL = 0.85
GELB_VERFUEGBAR_MB = 800
GELB_SWAP_ANTEIL = 0.60


def messen() -> dict:
    """Liest /proc/meminfo — die Werte in MB, wie Menschen sie lesen."""
    werte = {}
    for zeile in Path("/proc/meminfo").read_text().splitlines():
        name, _, rest = zeile.partition(":")
        werte[name] = int(rest.split()[0])  # kB

    swap_gesamt = werte.get("SwapTotal", 0)
    swap_benutzt = swap_gesamt - werte.get("SwapFree", 0)
    return {
        "verfuegbarMb": werte.get("MemAvailable", 0) // 1024,
        "gesamtMb": werte.get("MemTotal", 0) // 1024,
        "swapBenutztMb": swap_benutzt // 1024,
        "swapGesamtMb": swap_gesamt // 1024,
    }


def ampel(m: dict) -> str:
    swap_anteil = (
        m["swapBenutztMb"] / m["swapGesamtMb"] if m["swapGesamtMb"] else 0
    )
    if m["verfuegbarMb"] < ROT_VERFUEGBAR_MB or swap_anteil > ROT_SWAP_ANTEIL:
        return ROT
    if m["verfuegbarMb"] < GELB_VERFUEGBAR_MB or swap_anteil > GELB_SWAP_ANTEIL:
        return GELB
    return GRUEN


def _prozessbaum_rss(wurzel_pid: str) -> int:
    """Speicherverbrauch eines Prozesses samt aller Nachkommen, in MB.

    Über ps geht das ohne Wurzelrechte und ohne /proc-Gestocher: einmal alle
    Prozesse mit Eltern-PID und RSS holen, dann den Baum selbst ablaufen.
    """
    try:
        aus = subprocess.run(
            ["ps", "-eo", "pid=,ppid=,rss="],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (subprocess.TimeoutExpired, OSError):
        return 0

    kinder: dict[str, list[str]] = {}
    rss: dict[str, int] = {}
    for zeile in aus.splitlines():
        teile = zeile.split()
        if len(teile) != 3:
            continue
        pid, ppid, kb = teile
        kinder.setdefault(ppid, []).append(pid)
        try:
            rss[pid] = int(kb)
        except ValueError:
            rss[pid] = 0

    summe = 0
    stapel = [wurzel_pid]
    while stapel:
        pid = stapel.pop()
        summe += rss.get(pid, 0)
        stapel.extend(kinder.get(pid, []))
    return summe // 1024


def dickster_chat() -> dict | None:
    """Welche Sitzung auf dem hz-Socket gerade am meisten Speicher hält.

    Absichtlich direkt über tmux statt über hetzner_app.tmux: Der Wächter soll
    auch dann noch urteilen können, wenn im App-Code gerade etwas klemmt.
    """
    try:
        aus = subprocess.run(
            ["tmux", "-L", "hz", "list-panes", "-a",
             "-F", "#{session_name}\t#{pane_pid}"],
            capture_output=True, text=True, timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None
    if aus.returncode != 0:
        return None   # kein tmux-Server — dann gibt es auch keinen dicken Chat

    schwerster = None
    for zeile in aus.stdout.splitlines():
        name, _, pid = zeile.partition("\t")
        if not pid:
            continue
        mb = _prozessbaum_rss(pid.strip())
        # Der tmux-Präfix "hz-" ist Technik; auf der Karte steht der Name ohne.
        anzeige = name.removeprefix("hz-")
        if schwerster is None or mb > schwerster["mb"]:
            schwerster = {"name": anzeige, "mb": mb}
    return schwerster


def lesen() -> dict | None:
    """Der letzte Messstand — für die App-Anzeige."""
    try:
        return json.loads(DATEI.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _schreiben(stand: dict) -> None:
    DATEI.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=DATEI.parent, prefix=DATEI.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(stand, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATEI)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def lauf() -> dict:
    """Eine Messung: urteilen, festhalten, bei Umschlag auf Rot melden."""
    vorher = lesen() or {}
    m = messen()
    farbe = ampel(m)

    stand = {
        **m,
        "ampel": farbe,
        "zeit": int(time.time()),
        "dicksterChat": None,
    }

    if farbe == ROT:
        stand["dicksterChat"] = dickster_chat()

    # Nur der UMSCHLAG auf Rot klingelt. Rot bleibt Rot: still. Erst ein
    # Wechsel weg von Rot spannt die Feder für die nächste Meldung neu.
    if farbe == ROT and vorher.get("ampel") != ROT:
        text = (
            f"Nur noch {m['verfuegbarMb']} MB verfügbar, "
            f"Swap {m['swapBenutztMb']} von {m['swapGesamtMb']} MB voll."
        )
        if stand["dicksterChat"]:
            d = stand["dicksterChat"]
            text += f" Am dicksten: {d['name']} ({d['mb']} MB)."
        try:
            from . import melden
            melden.schicken("Speicher wird knapp", text)
        except Exception as fehler:
            # Die Messung ist auch ohne Klingel wertvoll — festhalten und den
            # Fehler ins Journal geben, statt den Lauf sterben zu lassen.
            print(f"Speicher-Meldung fehlgeschlagen: {fehler}", flush=True)

    _schreiben(stand)
    return stand


if __name__ == "__main__":
    ergebnis = lauf()
    print(json.dumps(ergebnis, ensure_ascii=False))
