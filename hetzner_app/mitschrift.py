"""Der Verlauf — ein Strang pro Projekt.

Claude Code schreibt jede Sitzung mit: vollständig, sauber getrennt nach
Sprecher, unter ~/.claude/projects/. Das ist die richtige Quelle — sie überlebt
jeden Neustart und reicht beliebig weit zurück.

Nur legt Claude Code für jedes Gespräch eine eigene Datei an, und in einem
Projektordner liegen darum Dutzende. Welche gehört zu dem Terminal, das gerade
auf dem Handy offen ist? Zweimal haben wir versucht, das zu beantworten, und
zweimal falsch: Erst nahmen wir die zuletzt beschriebene Datei — dann sprang
der Verlauf in ein fremdes Gespräch. Dann fragten wir den Claude-Prozess nach
seiner Kennung — die kennt er für sich selbst gar nicht, und der Verlauf war
ganz weg.

Jetzt stellen wir die Frage nicht mehr. Sie war von Anfang an die falsche:
Roli arbeitet nicht an Gesprächen, er arbeitet an Projekten. Ob er gestern am
Rechner, heute früh per Fernsteuerung und jetzt im Handy geredet hat, ist ihm
gleich — es ist dieselbe Arbeit am selben Ordner.

Also ziehen wir alle Mitschriften eines Ordners zu einem einzigen Strang
zusammen, chronologisch. Ein Projekt, ein Verlauf. Damit kann er gar nicht
mehr verschwinden: Es gibt nichts mehr zu verwechseln.
"""

from __future__ import annotations

import json
from pathlib import Path

PROJEKTE = Path.home() / ".claude" / "projects"


def _ordnername(cwd: str) -> str:
    """Aus einem Arbeitsordner wird der Name, unter dem Claude Code ihn ablegt.

    "/home/roli/projekte/KI WIKI" wird zu "-home-roli-projekte-KI-WIKI":
    Jedes Zeichen, das kein Buchstabe, keine Ziffer und kein Bindestrich ist,
    wird zum Bindestrich.
    """
    return "".join(c if c.isalnum() or c == "-" else "-" for c in cwd)


def _text_aus(inhalt) -> str:
    """Den lesbaren Text aus einem Nachrichteninhalt ziehen."""
    if isinstance(inhalt, str):
        return inhalt
    if not isinstance(inhalt, list):
        return ""

    stuecke = []
    for teil in inhalt:
        if isinstance(teil, dict) and teil.get("type") == "text":
            stuecke.append(teil.get("text", ""))
    return "\n\n".join(s for s in stuecke if s.strip())


def _bloecke_aus(eintrag: dict) -> list[dict]:
    """Aus einem Eintrag der Mitschrift werden die Blöcke, die im Handy stehen.

    Typen: du, claude, werkzeug, bild.
    """
    # Was ein Untergebener von Claude mit sich selbst bespricht, ist nicht Teil
    # der Unterhaltung — es ist sein innerer Monolog.
    if eintrag.get("isSidechain"):
        return []

    nachricht = eintrag.get("message")
    if not isinstance(nachricht, dict):
        return []

    zeit = eintrag.get("timestamp", "")
    uuid = eintrag.get("uuid", "")
    rolle = nachricht.get("role")
    inhalt = nachricht.get("content")

    def block(typ: str, text: str, datei: str = "") -> dict:
        return {
            "typ": typ,
            "text": text,
            "datei": datei,
            "zeilen": 0,
            "zeit": zeit,
            "uuid": uuid,
        }

    # --- Was du gesagt hast ---
    if rolle == "user":
        # Werkzeug-Ergebnisse kommen ebenfalls als "user" herein — das sind
        # aber keine Nachrichten von dir, sondern Rückmeldungen an Claude.
        if isinstance(inhalt, list) and any(
            isinstance(t, dict) and t.get("type") == "tool_result" for t in inhalt
        ):
            return []

        bloecke = []

        # Ein Bild, das du geschickt hast.
        if isinstance(inhalt, list):
            for teil in inhalt:
                if isinstance(teil, dict) and teil.get("type") == "image":
                    bloecke.append(block("bild", ""))
                    break

        text = _text_aus(inhalt).strip()
        if not text:
            return bloecke

        # Hinweise, die das System einstreut, sind nicht von dir:
        # Bild-Beschreibungen, Erinnerungen, Werkzeug-Rückmeldungen.
        if (
            text.startswith("<")
            or text.startswith("[Image:")
            or text.startswith("[Request interrupted")
            or "system-reminder" in text[:80]
            or "Called the Read tool" in text[:80]
        ):
            return bloecke

        # Ein Foto, das du über die App geschickt hast: Der Pfad steht als Text
        # da. Wir zeigen das Bild statt des Pfades.
        bild = ""
        for wort in text.split():
            if ".hetzner-bilder/" in wort:
                bild = wort.split(".hetzner-bilder/")[-1]
                text = text.replace(wort, "").strip()
                break

        bloecke.append(block("bild", text, bild) if bild else block("du", text))
        return bloecke

    # --- Was Claude geantwortet hat ---
    if rolle == "assistant" and isinstance(inhalt, list):
        bloecke = []
        for teil in inhalt:
            if not isinstance(teil, dict):
                continue

            # Sein Nachdenken gehört ihm, nicht in den Verlauf.
            if teil.get("type") == "thinking":
                continue

            if teil.get("type") == "text":
                text = teil.get("text", "").strip()
                if text:
                    bloecke.append(block("claude", text))

            elif teil.get("type") == "tool_use":
                werkzeug = teil.get("name", "?")
                # Der wichtigste Hinweis darauf, was das Werkzeug tat — meist
                # eine Datei oder ein Befehl.
                eingabe = teil.get("input", {})
                womit = ""
                if isinstance(eingabe, dict):
                    for schluessel in ("file_path", "command", "pattern", "path", "description"):
                        if eingabe.get(schluessel):
                            womit = str(eingabe[schluessel])
                            break

                # Lange Befehle abschneiden — sie sollen den Verlauf nicht
                # überschwemmen.
                if len(womit) > 70:
                    womit = womit[:67] + "…"

                bloecke.append(block("werkzeug", f"{werkzeug}({womit})" if womit else werkzeug))
        return bloecke

    return []


# --- Die Mitschriften lesen, ohne sie jedes Mal ganz zu lesen ----------------
#
# Das Handy fragt alle drei Sekunden nach dem Verlauf, und die Mitschriften
# eines langen Projekts sind zusammen viele Megabyte groß. Sie jedes Mal
# vollständig durchzukauen, hieße den Server im Leerlauf glühen zu lassen.
#
# Mitschriften werden nur hinten angehängt, nie umgeschrieben. Also merken wir
# uns pro Datei, bis wohin wir gelesen haben, und holen beim nächsten Mal nur
# das Neue nach.

_gemerkt: dict[Path, dict] = {}

# Mehr als so viele Blöcke zeigt das Handy ohnehin nie an. Was älter ist,
# dürfen wir aus dem Gedächtnis werfen — nachlesen könnten wir es notfalls
# wieder von der Platte.
_HOECHSTENS = 400


def _aus_datei(datei: Path) -> list[dict]:
    """Die Blöcke einer Mitschrift — frisch gelesen wird nur, was dazukam."""
    try:
        groesse = datei.stat().st_size
    except OSError:
        return []

    stand = _gemerkt.get(datei, {"gelesen": 0, "bloecke": []})

    # Ist die Datei kürzer als beim letzten Mal, ist sie nicht gewachsen,
    # sondern eine andere geworden. Dann fangen wir von vorne an.
    if groesse < stand["gelesen"]:
        stand = {"gelesen": 0, "bloecke": []}

    if groesse > stand["gelesen"]:
        try:
            with datei.open("rb") as f:
                f.seek(stand["gelesen"])
                neu = f.read()
        except OSError:
            return stand["bloecke"]

        # Claude schreibt womöglich gerade mitten in einer Zeile. Die nehmen
        # wir noch nicht — beim nächsten Mal ist sie fertig.
        schluss = neu.rfind(b"\n")
        if schluss >= 0:
            for zeile in neu[: schluss + 1].decode(errors="replace").splitlines():
                try:
                    eintrag = json.loads(zeile)
                except json.JSONDecodeError:
                    continue
                stand["bloecke"].extend(_bloecke_aus(eintrag))

            stand["gelesen"] += schluss + 1
            stand["bloecke"] = stand["bloecke"][-_HOECHSTENS:]

        _gemerkt[datei] = stand

    return stand["bloecke"]


def lesen(cwd: str, hoechstens: int = _HOECHSTENS) -> list[dict]:
    """Die Unterhaltung dieses Projekts — alle Gespräche, in einer Zeitleiste."""
    ordner = PROJEKTE / _ordnername(cwd)
    if not ordner.is_dir():
        return []

    alle: list[dict] = []
    for datei in ordner.glob("*.jsonl"):
        alle.extend(_aus_datei(datei))

    # Chronologisch. Der Zeitstempel steht in jedem Eintrag und ist überall
    # derselbe — auch über Gespräche und Rechner hinweg.
    alle.sort(key=lambda b: b["zeit"])

    # Wird ein Gespräch fortgesetzt oder zusammengefasst, schreibt Claude Code
    # das Bisherige in die neue Datei mit. Sonst stünde jeder Satz zweimal da.
    # Wir erkennen dieselbe Aussage an ihrer Kennung — und, falls die neu
    # vergeben wurde, an Zeitpunkt und Wortlaut.
    gesehen: set = set()
    strang: list[dict] = []
    for block in alle:
        merkmale = {(block["zeit"], block["typ"], block["text"][:80])}
        if block["uuid"]:
            merkmale.add(block["uuid"])
        if merkmale & gesehen:
            continue
        gesehen |= merkmale
        strang.append(block)

    return strang[-hoechstens:]
