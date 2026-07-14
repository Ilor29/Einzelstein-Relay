"""Aus Terminal-Gewusel wird eine lesbare Unterhaltung.

Im Terminal steht alles durcheinander: Claudes Text, Werkzeugaufrufe, Code,
Kästen, drehende Kreisel, Statuszeilen. Zum Arbeiten ist das richtig — zum
Nachlesen auf dem Handy ist es unerträglich.

Dieses Modul zerlegt den Bildschirm in Blöcke: was du gesagt hast, was Claude
geantwortet hat, welche Werkzeuge liefen, welcher Code entstand. Die App zeigt
den Text und klappt den Rest weg, bis du ihn sehen willst.

Es ist dieselbe Frage wie beim Vorlesen — was ist hier eigentlich der Inhalt? —
deshalb teilen sich beide die Filter aus tts.py.
"""

from __future__ import annotations

import re

from . import tts

# Deine Nachricht: ein Eingabepfeil mit Text dahinter.
_DU = re.compile(r"^[>❯]\s+(\S.*)$")

# Ein Foto, das du über die App geschickt hast. Im Terminal steht nur der Pfad —
# im Verlauf soll aber das Bild selbst zu sehen sein, sonst weiß man nach zehn
# Minuten nicht mehr, welches man geschickt hat.
_BILD = re.compile(r"((?:\S*/)?\.hetzner-bilder/([\w.-]+\.(?:jpg|png|webp|gif|heic)))")

# Ein Werkzeugaufruf: "⏺ Read(src/app.py)"
_WERKZEUG = re.compile(r"^⏺\s*(\w+)\((.*?)\)?\s*$")

# Die Ergebniszeile darunter: "⎿  42 Zeilen gelesen"
_ERGEBNIS = re.compile(r"^[⎿└]\s*(.*)$")


def _neuer_block(typ: str) -> dict:
    return {"typ": typ, "text": "", "zeilen": 0, "datei": ""}


def lesen(screen: str) -> list[dict]:
    """Zerlegt den Bildschirm in Blöcke.

    Jeder Block hat einen Typ:
      du        — was du geschrieben hast
      claude    — was Claude geantwortet hat
      werkzeug  — ein Werkzeugaufruf, zusammengefasst
      code      — ein Codeblock, eingeklappt
    """
    screen = tts.ohne_eingabekasten(screen)

    bloecke: list[dict] = []
    aktuell: dict | None = None

    def abschliessen() -> None:
        nonlocal aktuell
        if aktuell and (aktuell["text"].strip() or aktuell["zeilen"] or aktuell["datei"]):
            aktuell["text"] = aktuell["text"].strip()
            bloecke.append(aktuell)
        aktuell = None

    for zeile in screen.splitlines():
        text = tts.entkleide(zeile)

        if not text:
            # Eine Leerzeile beendet Text, aber nicht einen Codeblock — dort
            # gehören leere Zeilen dazu.
            if aktuell and aktuell["typ"] != "code":
                abschliessen()
            continue

        # Rahmen, Fußzeilen, Kreisel — alles, was kein Inhalt ist.
        if set(text) <= tts._RAHMEN or tts._FUSSZEILE.search(text):
            continue
        if tts._KREISEL.search(text):
            continue
        if text in {">", "❯", "$", "#"}:
            continue

        # Deine Nachricht.
        treffer = _DU.match(text)
        if treffer:
            abschliessen()
            gesagt = treffer.group(1)

            # Steckt ein Foto darin? Dann zeigen wir das Bild, nicht den Pfad.
            bild = _BILD.search(gesagt)
            # Bewusst nicht abschließen: Eine lange Nachricht bricht im
            # Terminal um, und die Fortsetzung gehört noch zu dir — nicht zu
            # Claude. Erst die nächste Leerzeile beendet sie.
            if bild:
                aktuell = _neuer_block("bild")
                aktuell["datei"] = bild.group(2)
                # Was du dazugeschrieben hast, wird zur Bildunterschrift.
                aktuell["text"] = _BILD.sub("", gesagt).strip()
            else:
                aktuell = _neuer_block("du")
                aktuell["text"] = gesagt

            continue

        # Ein Werkzeugaufruf.
        treffer = _WERKZEUG.match(text)
        if treffer:
            abschliessen()
            werkzeug, womit = treffer.group(1), (treffer.group(2) or "").strip()
            aktuell = _neuer_block("werkzeug")
            aktuell["text"] = f"{werkzeug}({womit})" if womit else werkzeug
            abschliessen()
            continue

        # Die Ergebniszeile eines Werkzeugs gehört zum Werkzeug, nicht zum Text.
        if _ERGEBNIS.match(text):
            continue

        # Code.
        if tts._ist_code(zeile):
            if not aktuell or aktuell["typ"] != "code":
                abschliessen()
                aktuell = _neuer_block("code")
            aktuell["text"] += zeile.rstrip() + "\n"
            aktuell["zeilen"] += 1
            continue

        # Alles andere ist Text — von Claude, oder die Fortsetzung deiner
        # eigenen umgebrochenen Nachricht.
        sauber = re.sub(r"^[⏺●·•*]\s*", "", text)
        if not sauber:
            continue

        # Läuft gerade eine Nachricht von dir — oder eine Bildunterschrift?
        # Dann gehört das noch dazu. Claudes Antwort beginnt immer nach einer
        # Leerzeile, und die hat den Block längst abgeschlossen.
        if aktuell and aktuell["typ"] in ("du", "bild"):
            aktuell["text"] = (aktuell["text"] + " " + sauber).strip()
            continue

        if not aktuell or aktuell["typ"] != "claude":
            abschliessen()
            aktuell = _neuer_block("claude")

        # Das Terminal bricht mitten im Satz um. Wir fügen wieder zusammen,
        # sonst liest sich der Text wie ein Telegramm.
        if aktuell["text"] and not aktuell["text"].endswith((" ", "\n")):
            aktuell["text"] += " "
        aktuell["text"] += sauber

    abschliessen()
    return bloecke
