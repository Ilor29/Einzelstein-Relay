"""Der Verlauf — aus den Mitschriften, die Claude Code selbst führt.

Bisher las die App den Terminal-Bildschirm ab und riet, wer was gesagt hat.
Das ging schief: Roli sah seine eigenen Sätze als Claudes Antworten, der
Verlauf reichte nur so weit zurück wie der Bildschirmspeicher, und nach einem
Neustart war er weg.

Dabei schreibt Claude Code jede Sitzung ohnehin mit — vollständig und sauber
getrennt nach Sprecher, unter ~/.claude/projects/. Das ist die richtige Quelle.
Nichts wird geraten, nichts geht verloren, und der Verlauf überlebt alles.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

PROJEKTE = Path.home() / ".claude" / "projects"


def _ordnername(cwd: str) -> str:
    """Aus einem Arbeitsordner wird der Name, unter dem Claude Code ihn ablegt.

    "/home/roli/projekte/KI WIKI" wird zu "-home-roli-projekte-KI-WIKI":
    Jedes Zeichen, das kein Buchstabe, keine Ziffer und kein Bindestrich ist,
    wird zum Bindestrich.
    """
    return "".join(c if c.isalnum() or c == "-" else "-" for c in cwd)


def datei_finden(cwd: str, kennung: str | None = None) -> Path | None:
    """Die Mitschrift der Sitzung, die in diesem Ordner läuft.

    Mit `kennung` — der Sitzungskennung des laufenden Claude — ist es eindeutig.
    Ohne sie bleibt nur die zuletzt beschriebene Datei, und das geht schief,
    sobald in demselben Projektordner ein zweites Gespräch läuft: Der Verlauf
    springt dann auf das fremde Gespräch um. Genau das ist passiert.
    """
    ordner = PROJEKTE / _ordnername(cwd)
    if not ordner.is_dir():
        return None

    if kennung:
        genannt = ordner / f"{kennung}.jsonl"
        if genannt.is_file():
            return genannt

    dateien = list(ordner.glob("*.jsonl"))
    if not dateien:
        return None

    return max(dateien, key=lambda p: p.stat().st_mtime)


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


def lesen(cwd: str, hoechstens: int = 400, kennung: str | None = None) -> list[dict]:
    """Die Unterhaltung als Blöcke — so, wie sie wirklich stattfand.

    Typen: du, claude, werkzeug, bild.
    """
    datei = datei_finden(cwd, kennung)
    if datei is None:
        return []

    bloecke: list[dict] = []

    with datei.open(errors="replace") as f:
        for zeile in f:
            try:
                eintrag = json.loads(zeile)
            except json.JSONDecodeError:
                continue

            nachricht = eintrag.get("message")
            if not isinstance(nachricht, dict):
                continue

            rolle = nachricht.get("role")
            inhalt = nachricht.get("content")

            # --- Was du gesagt hast ---
            if rolle == "user":
                # Werkzeug-Ergebnisse kommen ebenfalls als "user" herein — das
                # sind aber keine Nachrichten von dir, sondern Rückmeldungen an
                # Claude. Die gehören nicht in den Verlauf.
                if isinstance(inhalt, list) and any(
                    isinstance(t, dict) and t.get("type") == "tool_result" for t in inhalt
                ):
                    continue

                # Ein Bild, das du geschickt hast.
                if isinstance(inhalt, list):
                    for teil in inhalt:
                        if isinstance(teil, dict) and teil.get("type") == "image":
                            bloecke.append({"typ": "bild", "text": "", "datei": "", "zeilen": 0})
                            break

                text = _text_aus(inhalt).strip()
                if not text:
                    continue

                # Hinweise, die das System einstreut, sind nicht von dir:
                # Bild-Beschreibungen, Erinnerungen, Werkzeug-Rückmeldungen.
                if (
                    text.startswith("<")
                    or text.startswith("[Image:")
                    or text.startswith("[Request interrupted")
                    or "system-reminder" in text[:80]
                    or "Called the Read tool" in text[:80]
                ):
                    continue

                # Ein Foto, das du über die App geschickt hast: Der Pfad steht
                # als Text da. Wir zeigen das Bild statt des Pfades.
                bild = None
                for wort in text.split():
                    if ".hetzner-bilder/" in wort:
                        bild = wort.split(".hetzner-bilder/")[-1]
                        text = text.replace(wort, "").strip()
                        break

                if bild:
                    bloecke.append({"typ": "bild", "text": text, "datei": bild, "zeilen": 0})
                else:
                    bloecke.append({"typ": "du", "text": text, "datei": "", "zeilen": 0})
                continue

            # --- Was Claude geantwortet hat ---
            if rolle == "assistant" and isinstance(inhalt, list):
                for teil in inhalt:
                    if not isinstance(teil, dict):
                        continue

                    # Sein Nachdenken gehört ihm, nicht in den Verlauf.
                    if teil.get("type") == "thinking":
                        continue

                    if teil.get("type") == "text":
                        text = teil.get("text", "").strip()
                        if text:
                            bloecke.append(
                                {"typ": "claude", "text": text, "datei": "", "zeilen": 0}
                            )

                    elif teil.get("type") == "tool_use":
                        werkzeug = teil.get("name", "?")
                        # Der wichtigste Hinweis darauf, was das Werkzeug tat —
                        # meist eine Datei oder ein Befehl.
                        eingabe = teil.get("input", {})
                        womit = ""
                        if isinstance(eingabe, dict):
                            for schluessel in ("file_path", "command", "pattern", "path", "description"):
                                if eingabe.get(schluessel):
                                    womit = str(eingabe[schluessel])
                                    break

                        # Lange Befehle abschneiden — sie sollen den Verlauf
                        # nicht überschwemmen.
                        if len(womit) > 70:
                            womit = womit[:67] + "…"

                        bloecke.append({
                            "typ": "werkzeug",
                            "text": f"{werkzeug}({womit})" if womit else werkzeug,
                            "datei": "",
                            "zeilen": 0,
                        })

    return bloecke[-hoechstens:]
