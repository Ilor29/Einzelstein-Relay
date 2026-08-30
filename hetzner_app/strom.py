"""Vorlesen als EIN durchgehender Ton-Strom — das Radio-Prinzip.

Bisher holte sich die App jeden Satz einzeln als kleine Tondatei und reihte
die Häppchen im Browser mit Web Audio aneinander. Für Android ist so ein
Tonrechenwerk aber keine „Medienwiedergabe": Es bekommt keinen Platz auf dem
Sperrbildschirm und keinen Schutz in der Hosentasche — und genau dort blieb
Rolis Vortrag immer wieder stehen (30.08.: Ton-Uhr stand nach 19 Sekunden
Dunkelheit komplett still, Player meldete munter „spielt").

Ein Internet-Radio dagegen läuft in Chrome auf Android auch mit dunklem
Bildschirm weiter, samt Pause-Knopf auf dem Sperrbildschirm. Der Grund: ein
<audio>-Element mit einer ECHTEN Quelle (einer Adresse), aus der der Ton
fortlaufend nachkommt. Genau so ein Radiosender ist dieses Modul: Ein Vortrag
wird angemeldet, und unter seiner Adresse fließt eine einzige, endlos lange
WAV-Datei — Satz für Satz, sobald die Stimme ihn fertig hat. Der Browser
puffert voraus und spielt, was da ist.

Damit ALLE Stimmen in denselben Strom passen (Piper liefert WAV in
verschiedenen Abtastraten, die Wolken-Stimmen mp3), wird jedes Stück auf ein
gemeinsames Format gebracht: Mono, 16 Bit, 22.050 Hz. Was schon so ankommt
(die üblichen Piper-Stimmen), wird nur ausgepackt; alles andere übersetzt
ffmpeg.
"""

from __future__ import annotations

import asyncio
import logging
import re
import secrets
import struct
import subprocess
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from . import tts

log = logging.getLogger("hetzner_app.strom")

RATE = 22050                 # Abtastrate des Stroms — die der Piper-„medium"-Stimmen
_UNENDLICH = 0xFFFFFFFF      # „Länge unbekannt" im WAV-Kopf: der Strom hört nie auf

# Wie lange ein angemeldeter Vortrag abrufbar bleibt. Er wird beim Anmelden
# erzeugt und Sekunden später abgespielt; alles Ältere ist Müll.
_HALTBAR = 30 * 60


@dataclass
class Vortrag:
    stuecke: list[str]
    stimme: str | None = None          # None = die gewählte Stimme
    sitzung: str | None = None         # Folge-Modus: dort weiterlesen
    gelesen: str = ""                  # der Text, der schon in `stuecke` steckt
    erstellt: float = field(default_factory=time.time)
    fehler: str = ""                   # warum der Strom abgebrochen ist
    fertig: bool = False
    # Ab welcher Sekunde im Strom welches Stück beginnt — daraus liest die
    # App ab, welcher Satz gerade zu hören ist.
    startzeiten: list[float] = field(default_factory=list)


_vortraege: dict[str, Vortrag] = {}


def anmelden(text: str, stimme: str | None = None, sitzung: str | None = None) -> str:
    """Einen Vortrag registrieren; zurück kommt seine Kennung."""
    _aufraeumen()
    kennung = secrets.token_urlsafe(12)
    _vortraege[kennung] = Vortrag(
        stuecke=haeppchen(text), stimme=stimme, sitzung=sitzung, gelesen=text
    )
    return kennung


def holen(kennung: str) -> Vortrag | None:
    return _vortraege.get(kennung)


def _aufraeumen() -> None:
    grenze = time.time() - _HALTBAR
    for k in [k for k, v in _vortraege.items() if v.erstellt < grenze]:
        del _vortraege[k]


# --- Text in Häppchen -----------------------------------------------------------
#
# Das Gegenstück zu haeppchen() in app.js: An Satzenden trennen, das allererste
# Stück so klein wie möglich (damit der Ton sofort einsetzt), danach Portionen
# von rund 90 Zeichen, damit der Vortrag nicht zerhackt klingt.

_SATZ = re.compile(r"[\s\S]*?[.!?:]\s+|[\s\S]+$")


def haeppchen(text: str, mindestens: int = 90) -> list[str]:
    saetze = _SATZ.findall(text) or [text]
    stuecke: list[str] = []
    aktuell = ""
    for satz in saetze:
        aktuell += (" " if aktuell else "") + satz
        schwelle = 1 if not stuecke else mindestens
        if len(aktuell) >= schwelle:
            stuecke.append(aktuell)
            aktuell = ""
    if aktuell.strip():
        stuecke.append(aktuell)
    return [s for s in stuecke if s.strip()]


def neuer_teil(gelesen: str, voll: str) -> str | None:
    """Was `voll` über `gelesen` hinaus enthält — oder None, wenn nichts sauber
    anschließt (dann lieber aufhören als Falsches lesen)."""
    if len(voll) > len(gelesen) and voll.startswith(gelesen):
        return voll[len(gelesen):]
    return None


# --- Ton auf ein Format bringen -------------------------------------------------

def wav_kopf(rate: int = RATE) -> bytes:
    """Ein WAV-Kopf mit „Länge unbekannt" — der Browser spielt, was nachkommt."""
    return b"RIFF" + struct.pack("<I", _UNENDLICH) + b"WAVE" + \
        b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16) + \
        b"data" + struct.pack("<I", _UNENDLICH)


def _wav_zerlegen(audio: bytes) -> tuple[int, int, int, bytes] | None:
    """(Kanäle, Rate, Bits, Rohdaten) einer WAV-Datei — oder None, wenn es keine ist."""
    if len(audio) < 12 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        return None
    pos = 12
    kanaele = rate = bits = 0
    while pos + 8 <= len(audio):
        kennung = audio[pos:pos + 4]
        laenge = struct.unpack("<I", audio[pos + 4:pos + 8])[0]
        inhalt = audio[pos + 8:pos + 8 + laenge]
        if kennung == b"fmt " and len(inhalt) >= 16:
            fmt, kanaele, rate, _, _, bits = struct.unpack("<HHIIHH", inhalt[:16])
            if fmt != 1:
                return None            # kein einfaches PCM — soll ffmpeg machen
        elif kennung == b"data":
            if not (kanaele and rate and bits):
                return None
            # Piper meldet die Datenlänge gern als 0 oder „unendlich" — dann
            # ist alles bis zum Ende Ton.
            if laenge == 0 or laenge == _UNENDLICH or pos + 8 + laenge > len(audio):
                inhalt = audio[pos + 8:]
            return kanaele, rate, bits, inhalt
        pos += 8 + laenge + (laenge & 1)
    return None


def _uebersetzen(audio: bytes) -> bytes:
    """Beliebigen Ton (mp3, WAV in anderer Rate …) mit ffmpeg in Roh-PCM wandeln."""
    lauf = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-i", "pipe:0",
         "-f", "s16le", "-ac", "1", "-ar", str(RATE), "pipe:1"],
        input=audio, capture_output=True, timeout=60,
    )
    if lauf.returncode != 0 or not lauf.stdout:
        raise tts.TTSError("Der Ton ließ sich nicht in den Strom übersetzen.")
    return lauf.stdout


def pcm(audio: bytes) -> bytes:
    """Ein Tonstück als Roh-PCM (Mono, 16 Bit, RATE) — der Stoff des Stroms."""
    teile = _wav_zerlegen(audio)
    if teile and teile[0] == 1 and teile[1] == RATE and teile[2] == 16:
        return teile[3]
    return _uebersetzen(audio)


# --- Der Strom selbst ------------------------------------------------------------

TextHolen = Callable[[str], Awaitable[str]]
Arbeitet = Callable[[str], Awaitable[bool]]


async def _nachschub(v: Vortrag, text_holen: TextHolen, arbeitet: Arbeitet) -> str | None:
    """Folge-Modus: Hat Claude inzwischen weitergeschrieben? Dann den neuen
    Teil liefern; ist er fertig und nichts kommt nach, None.

    Das war früher Sache der App — und die friert Android in der Hosentasche
    ein. Hier auf dem Server läuft es weiter, egal was das Handy gerade tut."""
    if not v.sitzung:
        return None
    beginn = time.time()
    fertig_in_folge = 0
    fehler_in_folge = 0
    while time.time() - beginn < 30:
        try:
            voll = await text_holen(v.sitzung)
            fehler_in_folge = 0
        except Exception:
            fehler_in_folge += 1
            if fehler_in_folge >= 3:
                return None
            await asyncio.sleep(1.5)
            continue
        neu = neuer_teil(v.gelesen, voll)
        if neu:
            v.gelesen = voll
            return neu
        # Nichts Neues. Zweimal in Folge „Claude ruht" bestätigen, damit eine
        # kurze Atempause zwischen zwei Schritten nicht zu früh abbricht.
        try:
            beschaeftigt = await arbeitet(v.sitzung)
        except Exception:
            beschaeftigt = False
        fertig_in_folge = 0 if beschaeftigt else fertig_in_folge + 1
        if fertig_in_folge >= 2:
            return None
        await asyncio.sleep(0.7)
    return None


async def _stueck(v: Vortrag, i: int) -> bytes:
    audio = await tts.synthesize(v.stuecke[i], v.stimme)
    return await asyncio.to_thread(pcm, audio)


async def erstes_stueck(v: Vortrag, ab: int) -> bytes:
    """Das erste Stück VOR dem Strom holen — scheitert die Stimme, soll die
    App eine Meldung bekommen, keinen halb angefangenen Strom."""
    if ab >= len(v.stuecke):
        raise tts.TTSError("Da ist nichts zum Vorlesen.")
    return await _stueck(v, ab)


async def strom(v: Vortrag, ab: int, erstes: bytes,
                text_holen: TextHolen, arbeitet: Arbeitet):
    """Liefert den WAV-Strom Stück für Stück. Das jeweils nächste Stück wird
    schon gesprochen, während das aktuelle über die Leitung geht."""
    v.fertig = False
    v.fehler = ""
    v.startzeiten = v.startzeiten[:ab]
    yield wav_kopf()
    sekunden = 0.0
    i = ab
    daten: bytes | None = erstes
    naechstes: asyncio.Task | None = None
    try:
        while True:
            if daten is None:
                if i >= len(v.stuecke):
                    mehr = await _nachschub(v, text_holen, arbeitet)
                    if not mehr:
                        break
                    neue = haeppchen(mehr)
                    if not neue:
                        continue
                    v.stuecke.extend(neue)
                if naechstes is None:
                    naechstes = asyncio.create_task(_stueck(v, i))
                daten = await naechstes
                naechstes = None
            # Das übernächste Stück schon anstoßen, solange dieses unterwegs ist.
            if i + 1 < len(v.stuecke):
                naechstes = asyncio.create_task(_stueck(v, i + 1))
            while len(v.startzeiten) <= i:
                v.startzeiten.append(sekunden)
            v.startzeiten[i] = sekunden
            yield daten
            sekunden += len(daten) / (RATE * 2)
            daten = None
            i += 1
    except tts.TTSError as fehler:
        v.fehler = str(fehler)
        log.warning("Vortrag abgebrochen: %s", fehler)
    except asyncio.CancelledError:
        # Der Hörer hat aufgelegt (Stopp, Sprung, Seite weg). Nichts weiter
        # sprechen — das nächste Stück wäre für niemanden.
        if naechstes:
            naechstes.cancel()
        raise
    finally:
        if naechstes and not naechstes.done():
            naechstes.cancel()
        v.fertig = True
