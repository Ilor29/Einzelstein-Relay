"""Automatischer Kartenwechsel (Roli 02.11.2026 „19. Ja“, „20. Ja“).

Läuft per Cron alle 5 Minuten (`python3 -m hetzner_app.kartenwechsel`, Probelauf mit `--probe`).
Hat eine ruhige Karte mehr als 200.000 Token Kontext, dann:

1. Liegt im Projektordner keine frische UEBERGABE.md, bekommt die Karte den Auftrag, sie zu
   schreiben (einmal je drei Stunden; hat der Übergabe-Wächter schon einen Auftrag geschickt,
   wird nicht doppelt gefragt).
2. Liegt eine frische UEBERGABE.md vor und ist die Karte still, startet eine neue Karte im selben
   Ordner (gleiche Betriebsart und gleiches Modell), die Satz „Übergabe lesen“ als ersten Auftrag
   bekommt. Die alte Karte legt sich schlafen (bleibt in der Liste), Roli bekommt eine Telegram-Nachricht.

Schutz: nur eigene, nicht archivierte, nicht schlafende Karten im Zustand „idle“ oder „waiting“ ohne
offenen Dialog, seit mindestens zehn Minuten ohne Bewegung und nicht an einem Gerät geöffnet;
Karten, die sich einen Ordner teilen, bleiben außen vor; je Karte nur ein Wechsel. Ausschalten: Datei
~/.hetzner-app/kartenwechsel.aus anlegen.
"""
from __future__ import annotations

import collections
import json
import re
import sys
import time
from pathlib import Path

from . import state, tmux, verbrauch

GRENZE_TOKEN = 200_000
RUHE_S = 600                 # so lange muss die Karte still sein
UEBERGABE_FRISCH_S = 3600    # so jung muss die UEBERGABE.md sein
AUFTRAG_WIEDER_S = 3 * 3600  # frühestens nach so langer Zeit ein zweiter Schreib-Auftrag
SATZ = "Übergabe lesen"

STAND = Path.home() / ".hetzner-app" / "kartenwechsel.json"
AUS = Path.home() / ".hetzner-app" / "kartenwechsel.aus"
WAECHTER = Path.home() / ".hetzner-app" / "uebergabe-waechter.json"
LOG = Path.home() / "logs" / "kartenwechsel.log"

AUFTRAG = (
    "Automatischer Auftrag des Kartenwechsels: Der Kontext dieser Karte ist über 200.000 Token, "
    "weitere Züge werden teuer. Bitte jetzt den laufenden Stein sauber zu Ende bringen, Stand in "
    "Baubuch und Register nachtragen und UEBERGABE.md im Projektordner schreiben (Stand, offen, "
    "nächster Schritt, Beschlüsse mit Auslöser-Satz, Rolis letzter Wortlaut). Danach startet die App "
    "von selbst eine neue Karte mit „Übergabe lesen“. Roli ist vermutlich nicht am Gerät, bitte "
    "nichts Neues anfangen."
)


def log(text: str) -> None:
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(time.strftime("%d.%m. %H:%M ") + text + "\n")


def _json(pfad: Path) -> dict:
    try:
        return json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def naechster_name(alt: str, belegt: set[str]) -> str:
    """„Hetzner-App 11“ wird „Hetzner-App 12“; ohne Zahl hinten wird 2 angehängt."""
    m = re.match(r"^(.*?)(?:\s+(\d+))?$", alt.strip())
    basis, n = (m.group(1) or alt).strip(), int(m.group(2) or 1) + 1
    name = f"{basis} {n}"
    while name in belegt:
        n += 1
        name = f"{basis} {n}"
    return name


def uebergabe_frisch(cwd: str) -> bool:
    try:
        return time.time() - (Path(cwd) / "UEBERGABE.md").stat().st_mtime <= UEBERGABE_FRISCH_S
    except OSError:
        return False


def _telegram(text: str) -> None:
    sys.path.insert(0, str(Path.home() / "projekte" / "Brain" / "werkzeug"))
    from privat_telegram import senden
    senden(text)


def neue_karte(s: dict) -> str:
    """Startet die Folgekarte im selben Ordner und schickt ihr den Satz. Gibt ihren Namen zurück."""
    alt = s["name"]
    meta = state.get(alt)
    belegt = {x.name for x in tmux.list_sessions()} | state.vergebene_namen()
    name = naechster_name(alt, belegt)
    modell = meta.modell or ""
    kennung = tmux.create(name, s["cwd"], ohne_rueckfragen=bool(meta.ohne_rueckfragen), modell=modell)
    state.update(name, pinned=meta.pinned, notify_when_done=meta.notify_when_done, created_prompt=SATZ,
                 modell=modell, cwd=s["cwd"], ohne_rueckfragen=bool(meta.ohne_rueckfragen),
                 schlaeft=False, mitschrift=kennung)
    if not tmux.warte_bis_bereit(name, 40):
        raise RuntimeError(f"{name} wurde nicht bereit")
    zustand = tmux.dialog_zustand(name)
    if zustand == "vertrauensfrage":
        tmux.vertrauensfrage_beantworten(name)
        tmux.warte_bis_bereit(name, 15)
    elif zustand == "abbrechbar":
        tmux.send_key(name, "Escape")
        time.sleep(0.8)
    elif zustand == "anmeldung":
        raise RuntimeError(f"{name} zeigt den Anmelde-Bildschirm")
    tmux.send_text(name, SATZ)
    time.sleep(0.5)
    tmux.send_key(name, "Enter")
    return name


def alte_schlafen_legen(s: dict) -> None:
    name = s["name"]
    if state.detect(name) == state.RUNNING:
        return
    state.update(name, schlaeft=True, cwd=s["cwd"], schlaf_zeit=int(time.time()),
                 letzte_vorschau=state.preview(name))
    tmux.kill(name)


def main(argv: list[str]) -> None:
    probe = "--probe" in argv
    if AUS.exists():
        return
    gemerkt = _json(STAND)
    waechter = _json(WAECHTER)
    karten = [s for s in state.overview() if not s.get("archiviert") and s.get("eigen")]
    je_ordner = collections.Counter(s["cwd"] for s in karten if s["state"] != "sleeping")
    for s in karten:
        name = s["name"]
        if s["state"] not in ("idle", "waiting") or je_ordner[s["cwd"]] > 1:
            continue
        if s.get("attached") or (s.get("idleSeconds") or 0) < RUHE_S:
            continue
        k = verbrauch.kontext(s["cwd"]) or {}
        if k.get("benutzt", 0) < GRENZE_TOKEN:
            continue
        if tmux.dialog_zustand(name) != "frei":
            continue
        alt = gemerkt.get(name, {})
        if alt.get("gewechselt"):
            continue
        if uebergabe_frisch(s["cwd"]):
            if probe:
                print(f"WÜRDE wechseln: {name} ({k['benutzt']} Token), UEBERGABE.md ist frisch")
                continue
            try:
                neu = neue_karte(s)
            except Exception as e:  # noqa: BLE001
                log(f"Wechsel {name} fehlgeschlagen: {e}")
                continue
            alte_schlafen_legen(s)
            gemerkt[name] = {**alt, "gewechselt": int(time.time()), "neu": neu}
            _schreiben(gemerkt)
            log(f"{name} ({k['benutzt']} Token) -> {neu}, alte Karte schläft")
            try:
                _telegram(f"Kartenwechsel: „{name}“ hatte {k['benutzt'] // 1000}.000 Token Kontext. "
                          f"Die neue Karte „{neu}“ liest die Übergabe, die alte schläft.")
            except Exception as e:  # noqa: BLE001
                log(f"Telegram fehlgeschlagen: {e}")
            continue
        # keine frische Übergabe: einmal je drei Stunden um sie bitten, außer der Wächter hat es eben getan
        zuletzt = max(alt.get("auftrag", 0), waechter.get(name, {}).get("zeit", 0))
        if time.time() - zuletzt < AUFTRAG_WIEDER_S:
            continue
        if probe:
            print(f"WÜRDE um Übergabe bitten: {name} ({k['benutzt']} Token)")
            continue
        tmux.send_text(name, AUFTRAG)
        time.sleep(0.3)
        tmux.send_key(name, "Enter")
        gemerkt[name] = {**alt, "auftrag": int(time.time())}
        _schreiben(gemerkt)
        log(f"Übergabe-Auftrag an {name} ({k['benutzt']} Token)")


def _schreiben(gemerkt: dict) -> None:
    STAND.parent.mkdir(exist_ok=True)
    STAND.write_text(json.dumps(gemerkt, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
