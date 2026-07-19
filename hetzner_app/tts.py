"""Vorlesen — mit Piper, direkt auf dem Server.

Der schwierige Teil ist nicht das Sprechen, sondern das Aussortieren. Wer
Terminal-Ausgabe stur vorliest, hört minutenlang Dateipfade und Klammern.
Also: Fließtext wird vorgelesen, Code und Werkzeugaufrufe werden nur angesagt.
"""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import re
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

STIMMEN = Path.home() / ".hetzner-app" / "stimmen"
EINSTELLUNG = Path.home() / ".hetzner-app" / "stimme.txt"

# Das Stimmen-Angebot: EINE Datei = eine Stimme. Namen, die ein Mensch versteht
# statt der technischen Piper-Kennungen. Die zwei "Jonas" sind dieselbe Stimme in
# zwei Qualitäten.
#
# Bewusst NUR gemeinfreie Stimmen (CC0): Thorsten (Jonas/Jonas·fein/Max) und
# Kerstin (Marie). Die sind ohne jede Auflage verkaufbar — keine Namensnennung
# nötig. Die früheren MLS-Probestimmen (standen unter CC-BY, hätten einen Credit
# gebraucht) und die lizenz-unklaren M-AILABS-Stimmen sind bewusst raus (Stand
# 18.07.2026), damit an den Stimmen beim Verkauf keine Rechts-Auflage hängt.
#
# Tempo/Server (gemessen 18.07. auf dem kleinen Server): "Jonas" (medium) erzeugt
# Piper ~5x schneller als der Ton dauert → läuft flüssig, auch auf schwacher CPU.
# "Jonas · fein" (high) braucht etwa so lange wie der Ton selbst → auf dem kleinen
# Server entstehen Lücken zwischen den Sätzen. Sie ist die Premium-Stimme für
# einen stärkeren Server ("besserer Server, schönerer Klang"). Standard ist darum
# bewusst die schnelle.
KATALOG = {
    "de_DE-thorsten-medium": ("Jonas", "ruhig, schnell — flüssig auch auf kleinem Server"),
    "de_DE-thorsten-high": ("Jonas · fein", "besonders klar — braucht einen stärkeren Server"),
    "de_DE-thorsten_emotional-medium": ("Max", "lebhaft, betont"),
    # "Marie" (de_DE-kerstin-low) am 18.07. raus: rau, "low"-Qualität. Am
    # 19.07. dann MLS (CC-BY) durchprobiert — alle Frauenstimmen von Roli
    # verworfen (Aussprachefehler). Fazit: es gibt keine gute gemeinfreie
    # deutsche Frauenstimme. Bewusst KEINE im Angebot; wir bleiben bei Thorsten.
}

# Mehrstimmige Modelle (ein Modell, viele Sprecher) bieten wir derzeit NICHT an —
# die einzigen, die wir hatten (MLS), standen unter CC-BY. Die Maschinerie dafür
# (siehe _zerlegen_stimme und speaker_id in _sprechen) bleibt für später stehen;
# das Angebot ist leer.
#
# Am 19.07.2026 wurde MLS ausprobiert (das einzige deutsche Modell mit
# Frauenstimmen in „medium"): 236 Sprecher, per Tonhöhe/Klarheit die besten
# weiblichen herausgefiltert, sechs zur Probe eingebaut. Roli hat sie durchgehört
# und ALLE verworfen — Aussprachefehler, unsaubere Laute. Ergebnis: kein gutes
# gemeinfreies deutsches Frauenmodell verfügbar. Bewusste Entscheidung: wir
# bleiben rein bei Thorsten (CC0, keine Nennungsauflage), auch ohne Frauenstimme.
MEHRSTIMMIG: dict[str, tuple[str, str]] = {}

STANDARD = "de_DE-thorsten-medium"


def _zerlegen_stimme(name: str) -> tuple[str, int | None]:
    """Aus "datei#7" wird ("datei", 7); aus "datei" wird ("datei", None)."""
    if "#" in name:
        stem, sid = name.split("#", 1)
        return stem, int(sid)
    return name, None


def _stimme_gueltig(name: str) -> bool:
    stem, _ = _zerlegen_stimme(name)
    return (STIMMEN / f"{stem}.onnx").is_file() and (
        name in MEHRSTIMMIG or "#" not in name
    )


def stimmen() -> list[dict]:
    """Welche Stimmen auf diesem Server angeboten werden.

    Nur, was im Katalog steht — nichts, was zufällig im Ordner liegt (etwa alte,
    lizenz-unklare Modelle). Der Katalog IST das Angebot; so verkauft die App
    nur, was rechtlich sauber ist.
    """
    gewaehlt = gewaehlte_stimme()
    liste = []

    for stem, (anzeige, art) in KATALOG.items():
        if (STIMMEN / f"{stem}.onnx").is_file():
            liste.append({"name": stem, "anzeige": anzeige, "art": art,
                          "gewaehlt": stem == gewaehlt})

    for key, (anzeige, art) in MEHRSTIMMIG.items():
        stem = _zerlegen_stimme(key)[0]
        if (STIMMEN / f"{stem}.onnx").is_file():
            liste.append({"name": key, "anzeige": anzeige, "art": art,
                          "gewaehlt": key == gewaehlt})
    return liste


def gewaehlte_stimme() -> str:
    if EINSTELLUNG.exists():
        name = EINSTELLUNG.read_text().strip()
        if _stimme_gueltig(name):
            return name
    return STANDARD


def stimme_waehlen(name: str) -> None:
    if not _stimme_gueltig(name):
        raise ValueError("Diese Stimme gibt es nicht.")
    EINSTELLUNG.parent.mkdir(parents=True, exist_ok=True)
    EINSTELLUNG.write_text(name)


def modell(name: str | None = None) -> Path:
    stem, _ = _zerlegen_stimme(name or gewaehlte_stimme())
    return STIMMEN / f"{stem}.onnx"


class TTSError(RuntimeError):
    pass


# --- Der Piper-Prozess --------------------------------------------------------
#
# Piper läuft als EIGENES Programm, nicht mehr als Import in unserem Prozess.
# Zwei Gründe:
#
#  1. Lizenz. Piper ist GPL (über espeak-ng, das die Aussprache liefert). Als
#     getrennter Prozess hinter einer Schnittstelle bleibt unsere App ein
#     eigenes Werk — entscheidend, sobald sie verkauft wird. Beim Kunden
#     installiert der Einrichtungs-Weg Piper auf dessen Server; wir liefern
#     Piper nicht mit, wir reden nur mit ihm.
#  2. Robustheit. Stürzt Piper, stürzt nicht der Dienst — wir starten es neu.
#
# Der Prozess hält das Modell im Speicher, genau wie vorher der eigene. Deshalb
# kommt der erste Satz weiterhin sofort — die Vier-Sekunden-Wartezeit von
# früher (Modell bei jedem Vorlesen neu laden) bleibt Geschichte.

# Nur der eigene Rechner. Piper selbst würde an 0.0.0.0 binden — dann stünde
# das Vorlesen offen im Netz und jeder könnte den Server Aufsätze sprechen
# lassen.
_PORT = int(os.environ.get("HETZNER_TTS_PORT", "5005"))
_URL = f"http://127.0.0.1:{_PORT}"

# Was Piper zu erzählen hat (Startmeldungen, Fehler), landet hier — sonst wäre
# es beim Fehlersuchen einfach weg.
_LOG = Path.home() / ".hetzner-app" / "piper.log"

_prozess: subprocess.Popen | None = None
_sperre = threading.Lock()


def _laeuft() -> bool:
    return _prozess is not None and _prozess.poll() is None


def _gesund(frist: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(f"{_URL}/voices", timeout=frist):
            return True
    except OSError:
        return False


def _starten(warte: float = 20.0) -> None:
    """Startet den Piper-Prozess, falls nötig, und wartet, bis er bereit ist."""
    global _prozess
    with _sperre:
        if _laeuft() and _gesund():
            return
        if _prozess is not None and not _laeuft():
            _prozess = None       # toter Rest vom letzten Mal

        # Mit der gewählten Stimme starten, nicht mit der Standard-Stimme:
        # So ist genau das Modell sofort warm, das gleich sprechen soll. Alle
        # weiteren Stimmen lädt Piper bei Bedarf aus dem Stimmen-Ordner nach.
        datei = modell()
        if not datei.exists():
            raise TTSError(f"Die Stimme fehlt: {datei.name}")

        _LOG.parent.mkdir(parents=True, exist_ok=True)
        # Der Kindprozess braucht unsere Geheimnisse nicht (Zugangswort in
        # HETZNER_*-Variablen) — also bekommt er sie gar nicht erst.
        umgebung = {k: v for k, v in os.environ.items() if not k.startswith("HETZNER_")}
        # Die glibc-Speicherverwaltung zähmen: Ohne Deckel legt sie je Faden
        # eigene Speicher-Arenen an, und Piper hielt so 1,2 GB fest — mit
        # Deckel sind es ~160 MB nach dem Start und ~250 MB beim Sprechen,
        # bei UNVERÄNDERTEM Tempo (gemessen 19.07.: Jonas 0,16× Echtzeit, wie
        # vorher). Auf der kleinen Maschine ist das der Unterschied zwischen
        # eng und entspannt.
        umgebung.setdefault("MALLOC_ARENA_MAX", "2")
        # "wb": Bei jedem Prozess-Start beginnt das Log frisch. So enthält es
        # immer den letzten Lauf — und wächst nicht über Monate ins Uferlose.
        with open(_LOG, "wb") as log:
            _prozess = subprocess.Popen(
                [
                    sys.executable, "-m", "piper.http_server",
                    "-m", str(datei),
                    "--host", "127.0.0.1",
                    "--port", str(_PORT),
                    "--data-dir", str(STIMMEN),
                ],
                stdout=log,
                stderr=log,
                env=umgebung,
            )

    frist = time.monotonic() + warte
    while time.monotonic() < frist:
        if _gesund():
            return
        if not _laeuft():
            raise TTSError(
                "Der Piper-Prozess ist beim Start gestorben — siehe ~/.hetzner-app/piper.log"
            )
        time.sleep(0.2)
    raise TTSError("Der Piper-Prozess wurde nicht rechtzeitig bereit.")


def _beenden() -> None:
    """Den Piper-Prozess sauber stoppen (beim Herunterfahren des Dienstes)."""
    if _laeuft():
        _prozess.terminate()
        try:
            _prozess.wait(3)
        except subprocess.TimeoutExpired:
            _prozess.kill()


atexit.register(_beenden)


def _sprechen(text: str, name: str) -> bytes:
    """Die eigentliche Arbeit — läuft in einem Nebenläufer, damit der Dienst
    weiter antwortet, während gesprochen wird."""
    stem, sprecher = _zerlegen_stimme(name)

    anfrage: dict = {"text": text, "voice": stem}
    if sprecher is not None:
        # Bei mehrstimmigen Modellen den gewählten Sprecher setzen; bei
        # Einzelstimmen bleibt es beim Standard.
        anfrage["speaker_id"] = sprecher
    daten = json.dumps(anfrage).encode()

    for versuch in (1, 2):
        _starten()
        try:
            aufruf = urllib.request.Request(
                _URL, data=daten, headers={"Content-Type": "application/json"}
            )
            # Lange Absätze brauchen ihre Zeit — großzügig bemessen.
            with urllib.request.urlopen(aufruf, timeout=120) as antwort:
                return antwort.read()
        except urllib.error.HTTPError as fehler:
            # Piper LEBT und meldet einen Fehler (etwa: leerer Text). Das ist
            # kein Absturz — ein Neustart würde nur das warme Modell wegwerfen
            # und den nächsten echten Satz den Kaltstart zahlen lassen.
            raise TTSError(f"Piper lehnt ab (HTTP {fehler.code}) — siehe ~/.hetzner-app/piper.log")
        except OSError:
            if versuch == 2:
                raise TTSError(
                    "Piper antwortet nicht — siehe ~/.hetzner-app/piper.log"
                )
            # Verbindungsfehler: Der Prozess ist wohl wirklich gestorben.
            # Einmal neu starten, nochmal versuchen — erst dann aufgeben.
            _beenden()
    raise TTSError("Unerreichbar")   # nur für den Typ-Prüfer; oben kehrt immer zurück


def vorladen() -> None:
    """Den Piper-Prozess samt gewählter Stimme beim Start hochfahren."""
    try:
        _starten()
    except Exception:
        # Fehlt die Stimme, merkt man es beim ersten Vorlesen — der Dienst darf
        # daran nicht scheitern.
        pass


async def synthesize(text: str, stimme: str | None = None) -> bytes:
    """Macht aus Text eine WAV-Datei — mit der gewählten Stimme."""
    name = stimme or gewaehlte_stimme()
    # Letzte Sicherung: Was hier ankommt, ist schon aufbereitet — aber ein
    # übriggebliebenes Sternchen liest Piper gnadenlos mit vor. Also nochmal
    # drüber, ganz kurz vor dem Mund.
    sauber = symbole_weg(text)
    # Bleibt danach nichts übrig (etwa bei "***"), gar nicht erst zu Piper —
    # der antwortete darauf nur mit einem Fehler.
    if not sauber.strip():
        raise TTSError("Da ist nichts Vorlesbares übrig geblieben.")
    return await asyncio.to_thread(_sprechen, sauber, name)


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


# --- Markdown zum Hören ------------------------------------------------------
#
# Claudes Antworten sind Markdown: Sternchen für Betonung, Rückstriche für Code,
# Rauten für Überschriften, Klammern für Verweise. Zum Lesen ist das schön, zum
# Hören ist es Kauderwelsch — Piper liest jedes Zeichen brav mit ("Sternchen
# Sternchen fertig Sternchen Sternchen"). Hier fliegt es raus, bevor gesprochen
# wird.
#
# Anders als `for_speech`, das Terminal-Bildschirme aufräumt, arbeitet das hier
# auf der sauberen Antwort aus der Mitschrift.

_ZAUN = re.compile(r"^\s*(```|~~~)")
_TABELLEN_LINIE = re.compile(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$")
_TRENNLINIE = re.compile(r"^\s*([-*_=])\1{2,}\s*$")

_BILD = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_VERWEIS = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_CODE_SPANNE = re.compile(r"`+([^`]*)`+")
_BETONUNG = re.compile(r"(\*\*|\*|__|_|~~)(?=\S)(.+?\S)\1")
_ZEILEN_ANFANG = re.compile(r"^\s*(#{1,6}\s+|>\s+|[-*+•·⏺●]\s+|\d+[.)]\s+)")

# Was danach noch stört: Kastengrafik, Sternchen, Rückstriche, Rauten, Pfeile.
# Nichts davon will man hören, und Piper stolpert darüber.
_REST_ZEICHEN = re.compile(
    r"[*`#|~<>{}\[\]│┃─━╭╮╰╯┌┐└┘├┤┬┴┼═║▌▐█░▒▓⏺✻✽✢→←↔⇒➜•·●]+"
)


def symbole_weg(text: str) -> str:
    """Zieht die letzten Sonderzeichen ab und glättet die Leerstellen."""
    sauber = _REST_ZEICHEN.sub(" ", text)
    zeilen = [re.sub(r"[ \t]+", " ", z).strip() for z in sauber.splitlines()]
    return "\n".join(z for z in zeilen if z).strip()


def _codeblock_ansage(zeilen: int) -> str:
    wort = "Zeile" if zeilen == 1 else "Zeilen"
    return f"Codeblock, {zeilen} {wort}."


def fuer_stimme(text: str) -> str:
    """Macht aus einer Markdown-Antwort etwas, das man sich anhören kann.

    Code wird angesagt statt vorgelesen, Auszeichnung fällt weg, der Fließtext
    bleibt.
    """
    absaetze: list[str] = []
    im_code = False
    code_zeilen = 0

    for zeile in text.splitlines():
        # Ein Code-Zaun schaltet um: Was dazwischen steht, wird gezählt.
        if _ZAUN.match(zeile):
            if im_code:
                absaetze.append(_codeblock_ansage(code_zeilen))
                code_zeilen = 0
            im_code = not im_code
            continue

        if im_code:
            if zeile.strip():
                code_zeilen += 1
            continue

        satz = _zeile_fuer_stimme(zeile)
        if satz:
            absaetze.append(satz)

    # Ein Zaun, der nie zuging — trotzdem ansagen, was drinstand.
    if im_code and code_zeilen:
        absaetze.append(_codeblock_ansage(code_zeilen))

    return "\n".join(absaetze).strip()


def _klingt_wie_code(text: str) -> bool:
    """Viele Sonderzeichen, wenig Wörter — das will niemand hören.

    Wie `_ist_code`, aber ohne die Einrückungs-Regel: In Markdown ist eine
    eingerückte Zeile meistens ein Unterpunkt, kein Code.
    """
    sonderzeichen = len(_CODE_ZEICHEN.findall(text))
    return sonderzeichen >= 3 and sonderzeichen > len(text.split()) / 2


def _zeile_fuer_stimme(zeile: str) -> str:
    text = entkleide(zeile)
    if not text:
        return ""

    # Trennlinien und die Strich-Zeile unter einer Tabellenüberschrift sind
    # reine Optik.
    if _TRENNLINIE.match(text) or _TABELLEN_LINIE.match(text):
        return ""

    text = _BILD.sub("", text)
    text = _VERWEIS.sub(r"\1", text)         # Verweis: der Text zählt, nicht die Adresse
    text = _CODE_SPANNE.sub(r"\1", text)     # Rückstriche weg, der Inhalt bleibt
    text = _ZEILEN_ANFANG.sub("", text)      # Raute, Zitatpfeil, Aufzählungspunkt

    # Betonung zweimal abziehen — **fett mit *kursiv* drin** ist verschachtelt.
    text = _BETONUNG.sub(r"\2", text)
    text = _BETONUNG.sub(r"\2", text)

    # Erst JETZT prüfen, ob es Code ist — am rohen Markdown gemessen hielte die
    # Prüfung jeden Verweis und jedes Wort in Rückstrichen für Code und
    # verschluckte den ganzen Satz drumherum.
    if _klingt_wie_code(text):
        return ""

    return symbole_weg(text)
