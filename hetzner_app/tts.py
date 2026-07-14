"""Vorlesen — mit Piper, direkt auf dem Server.

Der schwierige Teil ist nicht das Sprechen, sondern das Aussortieren. Wer
Terminal-Ausgabe stur vorliest, hört minutenlang Dateipfade und Klammern.
Also: Fließtext wird vorgelesen, Code und Werkzeugaufrufe werden nur angesagt.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

STIMMEN = Path.home() / ".hetzner-app" / "stimmen"
EINSTELLUNG = Path.home() / ".hetzner-app" / "stimme.txt"

# Die Stimmen, die wir kennen — mit Namen, die ein Mensch versteht.
KATALOG = {
    "de_DE-thorsten-medium": ("Thorsten", "männlich, ruhig"),
    "de_DE-karlsson-low": ("Karlsson", "männlich, hell"),
    "de_DE-eva_k-x_low": ("Eva", "weiblich, weich"),
    "de_DE-kerstin-low": ("Kerstin", "weiblich, klar"),
    "de_DE-ramona-low": ("Ramona", "weiblich, warm"),
}

STANDARD = "de_DE-thorsten-medium"


def stimmen() -> list[dict]:
    """Welche Stimmen auf diesem Server bereitliegen."""
    gewaehlt = gewaehlte_stimme()
    liste = []
    for datei in sorted(STIMMEN.glob("*.onnx")):
        name = datei.stem
        anzeige, art = KATALOG.get(name, (name, ""))
        liste.append({
            "name": name,
            "anzeige": anzeige,
            "art": art,
            "gewaehlt": name == gewaehlt,
        })
    return liste


def gewaehlte_stimme() -> str:
    if EINSTELLUNG.exists():
        name = EINSTELLUNG.read_text().strip()
        if (STIMMEN / f"{name}.onnx").is_file():
            return name
    return STANDARD


def stimme_waehlen(name: str) -> None:
    if not (STIMMEN / f"{name}.onnx").is_file():
        raise ValueError("Diese Stimme gibt es nicht.")
    EINSTELLUNG.parent.mkdir(parents=True, exist_ok=True)
    EINSTELLUNG.write_text(name)


def modell(name: str | None = None) -> Path:
    return STIMMEN / f"{name or gewaehlte_stimme()}.onnx"


class TTSError(RuntimeError):
    pass


def _finde_piper() -> str | None:
    """Sucht Piper — auch dort, wo pip es hinlegt.

    Startet man den Server mit .venv/bin/python, liegt .venv/bin trotzdem
    nicht im Suchpfad. Also erst dort nachsehen, wo unser eigenes Python liegt.
    """
    neben_python = Path(sys.executable).parent / "piper"
    if neben_python.is_file():
        return str(neben_python)
    return shutil.which("piper")


async def synthesize(text: str, stimme: str | None = None) -> bytes:
    """Macht aus Text eine WAV-Datei — mit der gewählten Stimme."""
    piper = _finde_piper()
    if not piper:
        raise TTSError(
            "Piper ist nicht installiert. Führe scripts/install-piper.sh aus."
        )

    datei = modell(stimme)
    if not datei.exists():
        raise TTSError(f"Die Stimme fehlt: {datei.stem}")

    # In eine Datei schreiben lassen, nicht auf die Standardausgabe.
    #
    # Piper nimmt "--output_file -" zwar an und läuft fehlerfrei durch, liefert
    # dabei aber nichts — man bekommt eine leere Antwort und keinen Hinweis
    # warum. In eine Datei schreibt es zuverlässig.
    with tempfile.TemporaryDirectory() as ordner:
        ziel = Path(ordner) / "gesprochen.wav"

        process = await asyncio.create_subprocess_exec(
            piper,
            "--model", str(datei),
            "--output_file", str(ziel),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, fehler = await process.communicate(text.encode())

        if process.returncode != 0:
            raise TTSError(f"Piper ist ausgestiegen: {fehler.decode(errors='replace')}")
        if not ziel.exists():
            raise TTSError("Piper hat nichts gesprochen.")

        return ziel.read_bytes()


# --- Aufbereitung ------------------------------------------------------------

# Kästen, Trennlinien und die Blockgrafik des Begrüßungsbanners.
_RAHMEN = set("─│╭╮╰╯┌┐└┘├┤┬┴┼━┃═║▐▌▛▜▙▟▝▘▗▖▄▀█░▒▓▎▏▕ ")

# Ein Werkzeugaufruf: "⏺ Read(src/app.py)" — erkennbar an der Klammer.
# Ohne Klammer beginnt hinter dem Punkt Claudes Fließtext, den wir vorlesen
# wollen; die Klammer ist der ganze Unterschied.
_WERKZEUG = re.compile(r"^⏺\s*(\w+)\(")

# Der Kreisel, während Claude arbeitet: "✻ Sautéed for 3s (esc to interrupt)"
_KREISEL = re.compile(r"^[✻✽✢·*∗]\s|for \d+s\b")

# Sieht die Zeile nach Code aus? Viele Sonderzeichen, wenig Wörter.
_CODE_ZEICHEN = re.compile(r"[{}()\[\];=<>|&$/\\]")

# Zeug, das ständig auf dem Schirm steht und niemanden interessiert: die
# Fußzeile von Claude Code und das Begrüßungsbanner.
_FUSSZEILE = re.compile(
    r"(esc to interrupt|tokens|Context left|shift\+tab|\? for shortcuts"
    r"|manual mode|auto mode|for agents|What's new|Claude Max|Opus \d|Sonnet \d"
    r"|cwd:|/help for help"
    # Was Claude Code über sich selbst meldet, ist keine Antwort an dich.
    r"|Running \d+ (shell |background )?command|Waiting…|Thinking…"
    # Hinweiszeilen von Claude Code hängen ihre Tipps mit Mittelpunkten
    # aneinander: "tmux detected · scroll with PgUp · or add 'set -g mouse on'".
    # Zwei Mittelpunkte in einer Zeile kommen in Fließtext praktisch nie vor.
    r"|\S+ · \S+.* · )",
    re.IGNORECASE,
)


def entkleide(zeile: str) -> str:
    """Zieht Kastenwände und Blockgrafik von einer Zeile ab.

    Claude Code malt seine Ausgabe in Kästen und stellt Dinge nebeneinander.
    Steht in einer Zeile mehr als eine Kastenwand, ist es ein zweispaltiges
    Layout — dann zählt nur die erste Spalte, der Rest ist Zierrat.
    """
    text = zeile.strip()
    if text.count("│") > 1:
        text = text.split("│", 2)[1] if text.startswith("│") else text.split("│")[0]
    return text.strip().strip("│┃|").strip()


def _ist_code(zeile: str) -> bool:
    text = zeile.strip()
    if not text:
        return False
    # Eingerückt wie ein Codeblock.
    if zeile.startswith("    ") and len(text) > 3:
        return True
    # Mehr Sonderzeichen als ein Fließtext je hätte.
    sonderzeichen = len(_CODE_ZEICHEN.findall(text))
    return sonderzeichen >= 3 and sonderzeichen > len(text.split()) / 2


def ohne_eingabekasten(screen: str) -> str:
    """Schneidet den Eingabekasten am unteren Rand ab.

    Er steht immer unten, zwischen zwei durchgehenden Linien, und enthält bei
    leerer Eingabe einen grauen Beispieltext ('Try "fix lint errors"'). Der
    ist weder Inhalt noch Antwort — er darf weder in der Vorschau auftauchen
    noch vorgelesen werden.
    """
    zeilen = screen.splitlines()

    # Die Trennlinien von unten her suchen.
    linien = [
        i for i, z in enumerate(zeilen)
        if z.strip() and set(z.strip()) <= {"─", "━", "-"}
    ]
    if len(linien) >= 2:
        return "\n".join(zeilen[:linien[-2]])
    return screen


def letzte_antwort(screen: str) -> str:
    """Schneidet alles vor deiner letzten Nachricht ab.

    Du willst hören, was Claude gerade geantwortet hat — nicht den halben
    Gesprächsverlauf und schon gar nicht die Hinweisbanner vom Programmstart.
    Deine eigenen Nachrichten stehen im Terminal hinter einem ">".
    """
    zeilen = screen.splitlines()

    for i in range(len(zeilen) - 1, -1, -1):
        text = entkleide(zeilen[i])
        # Deine Nachricht: ein ">" mit Text dahinter. Die leere
        # Eingabeaufforderung am Ende zählt nicht.
        if re.match(r"^[>❯]\s+\S", text):
            return "\n".join(zeilen[i + 1:])

    return screen


def for_speech(screen: str, nur_letzte: bool = True) -> str:
    """Macht aus dem Terminal-Inhalt etwas, das man sich anhören kann."""
    screen = ohne_eingabekasten(screen)
    if nur_letzte:
        screen = letzte_antwort(screen)

    absaetze: list[str] = []
    satz: list[str] = []
    code_zeilen = 0
    werkzeuge: list[str] = []

    def satz_abschliessen() -> None:
        nonlocal satz
        if satz:
            absaetze.append(" ".join(satz))
            satz = []

    def code_abschliessen() -> None:
        nonlocal code_zeilen
        if code_zeilen:
            wort = "Zeile" if code_zeilen == 1 else "Zeilen"
            absaetze.append(f"Codeblock, {code_zeilen} {wort}.")
            code_zeilen = 0

    def werkzeuge_abschliessen() -> None:
        nonlocal werkzeuge
        if werkzeuge:
            if len(werkzeuge) == 1:
                absaetze.append(f"Werkzeug benutzt: {werkzeuge[0]}.")
            else:
                absaetze.append(f"{len(werkzeuge)} Werkzeuge benutzt.")
            werkzeuge = []

    for zeile in screen.splitlines():
        # Kastenwände abziehen, sonst hält die leere Eingabezeile sich für
        # Inhalt, bloß weil ein Eingabepfeil darin steht.
        text = entkleide(zeile)

        # Leerzeile beendet den laufenden Satz.
        if not text:
            satz_abschliessen()
            code_abschliessen()
            werkzeuge_abschliessen()
            continue

        # Rahmen, Fußzeile, Kreisel und die leere Eingabeaufforderung raus.
        if set(text) <= _RAHMEN or _FUSSZEILE.search(text):
            continue
        if _KREISEL.search(text):
            continue
        if text in {">", "❯", "$", "#"}:
            continue

        # Werkzeugaufrufe werden gezählt, nicht vorgelesen.
        treffer = _WERKZEUG.match(text)
        if treffer:
            satz_abschliessen()
            code_abschliessen()
            werkzeuge.append(treffer.group(1))
            continue

        if _ist_code(zeile):
            satz_abschliessen()
            werkzeuge_abschliessen()
            code_zeilen += 1
            continue

        # Echter Fließtext.
        code_abschliessen()
        werkzeuge_abschliessen()

        # Führende Aufzählungszeichen und Eingabepfeile weg.
        text = re.sub(r"^[>❯*·•●⏺\-\s]+", "", text)
        if not text:
            continue

        satz.append(text)

        # Endet die Zeile auf ein Satzzeichen, ist der Satz zu Ende. Sonst
        # gehört die nächste Zeile dazu — das Terminal bricht ja mitten im
        # Satz um, und zerhackt vorgelesen klingt es fürchterlich.
        if text.endswith((".", "!", "?", ":")):
            satz_abschliessen()

    satz_abschliessen()
    code_abschliessen()
    werkzeuge_abschliessen()

    return "\n".join(absaetze).strip()
