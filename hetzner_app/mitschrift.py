"""Der Verlauf — aus den Mitschriften, die Claude Code selbst führt.

Bisher las die App den Terminal-Bildschirm ab und riet, wer was gesagt hat.
Das ging schief: Roli sah seine eigenen Sätze als Claudes Antworten, der
Verlauf reichte nur so weit zurück wie der Bildschirmspeicher, und nach einem
Neustart war er weg.

Dabei schreibt Claude Code jede Sitzung ohnehin mit — vollständig und sauber
getrennt nach Sprecher, unter ~/.claude/projects/. Das ist die richtige Quelle.
Nichts wird geraten, nichts geht verloren, und der Verlauf überlebt alles.

Bleibt die eine schwierige Frage: Welche der vielen Mitschriften in einem
Projektordner gehört zu der Sitzung, die gerade auf dem Handy offen ist?
Darum geht es weiter unten, bei `finden`.
"""

from __future__ import annotations

import json
import re
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
    """Die Mitschrift mit dieser Kennung — oder notfalls die jüngste im Ordner."""
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


# --- Welche Mitschrift gehört zu dieser Sitzung? -----------------------------
#
# Die schwierigste Frage der ganzen App. In einem Projektordner liegen Dutzende
# Mitschriften — jedes Gespräch, das je in diesem Ordner lief. Welche davon
# gehört zu dem Terminal, das gerade auf dem Handy offen ist?
#
# Zweimal haben wir es falsch beantwortet. Erst nahmen wir die zuletzt
# beschriebene Datei; dann sprang der Verlauf in ein fremdes Gespräch, sobald
# im selben Ordner ein zweites lief. Dann fragten wir den Claude-Prozess nach
# seiner Kennung in der Umgebung — aber die setzt Claude Code nicht für sich
# selbst, sondern nur für Programme, die es startet. Also fanden wir entweder
# gar nichts (und rieten wieder) oder die Kennung des fremden Claude, der das
# Terminal einst gestartet hatte. Der Verlauf war weg.
#
# Jetzt fragen wir niemanden mehr. Wir vergleichen: Auf dem Bildschirm der
# Sitzung steht die Unterhaltung — und in der richtigen Mitschrift stehen
# dieselben Sätze. Die Datei, deren letzte Sätze auf dem Schirm wiederzufinden
# sind, ist die richtige. Das ist keine Vermutung, das ist ein Beweis.

# Zum Vergleichen lassen wir alles weg, was das Terminal verändert: Umbrüche
# mitten im Satz, doppelte Leerzeichen, Rahmen, Groß- und Kleinschreibung.
def _verdichtet(text: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]", "", text.lower())


# Kurze Sätze taugen nicht als Beweis: "Ja." oder "Weiter" steht in jedem
# zweiten Gespräch. Erst ab dieser Länge ist ein Satz eindeutig genug.
_BEWEISLAENGE = 30


def _letzte_saetze(datei: Path, wieviele: int = 4) -> list[str]:
    """Die letzten gesprochenen Sätze einer Mitschrift.

    Nur das Ende der Datei wird gelesen — sie werden viele Megabyte groß, und
    das Handy fragt alle drei Sekunden nach.
    """
    try:
        groesse = datei.stat().st_size
        with datei.open("rb") as f:
            f.seek(max(0, groesse - 200_000))
            schwanz = f.read().decode(errors="replace")
    except OSError:
        return []

    saetze: list[str] = []
    # Die erste Zeile ist nach dem Sprung meist angeschnitten — die überspringt
    # der JSON-Fehler von selbst.
    for zeile in reversed(schwanz.splitlines()):
        try:
            eintrag = json.loads(zeile)
        except json.JSONDecodeError:
            continue

        nachricht = eintrag.get("message")
        if not isinstance(nachricht, dict):
            continue
        if nachricht.get("role") not in ("user", "assistant"):
            continue

        text = _text_aus(nachricht.get("content")).strip()
        if len(_verdichtet(text)) >= _BEWEISLAENGE:
            saetze.append(text)
        if len(saetze) >= wieviele:
            break

    return saetze


def _steht_auf_dem_schirm(datei: Path, schirm: str) -> bool:
    """Findet sich diese Mitschrift auf dem Bildschirm der Sitzung wieder?"""
    for satz in _letzte_saetze(datei):
        # Ein Ausschnitt genügt: Lange Nachrichten kürzt das Terminal, und die
        # ersten Zeichen stehen immer da.
        probe = _verdichtet(satz)[:60]
        if len(probe) >= _BEWEISLAENGE and probe in schirm:
            return True
    return False


def finden(cwd: str, schirm: str, zuletzt: str = "") -> str | None:
    """Die Kennung der Mitschrift, die zu diesem Bildschirm gehört.

    `zuletzt` ist die Kennung, bei der wir letztes Mal gelandet sind. Sie ist
    fast immer noch richtig — also prüfen wir sie zuerst und lesen im Normalfall
    nur eine einzige Datei an.
    """
    ordner = PROJEKTE / _ordnername(cwd)
    if not ordner.is_dir():
        return None

    verdichtet = _verdichtet(schirm)

    if zuletzt:
        datei = ordner / f"{zuletzt}.jsonl"
        if datei.is_file() and _steht_auf_dem_schirm(datei, verdichtet):
            return zuletzt

    # Die bekannte Kennung passt nicht mehr — etwa nach /clear, nach einem
    # Neustart der Sitzung, oder weil wir sie noch nie kannten. Also suchen wir
    # von vorn, die zuletzt beschriebenen Dateien zuerst.
    dateien = sorted(
        ordner.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    for datei in dateien[:20]:
        if _steht_auf_dem_schirm(datei, verdichtet):
            return datei.stem

    # Nichts passt. Das ist der Normalfall bei einer frischen Sitzung: Es steht
    # noch nichts auf dem Schirm, was man wiederfinden könnte. Dann bleibt es
    # bei dem, was wir wissen — und lieber gar nichts als ein fremdes Gespräch.
    return zuletzt or None


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
