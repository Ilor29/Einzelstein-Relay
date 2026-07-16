"""Anmeldung ohne Passwort — über einen Schlüssel, der auf deinem Gerät bleibt.

Der Gedanke: Ein Passwort muss irgendwie vom Server zu dir wandern, und
unterwegs bleibt es überall liegen — im Chat, in der Mail, im Verlauf. Ein
Schlüsselpaar wandert nicht. Der geheime Teil entsteht auf deinem Handy und
verlässt es nie; nur der öffentliche Teil kommt hierher, und der ist kein
Geheimnis. Er darf in jedem Chat stehen.

Angemeldet wird sich dann so: Der Server stellt eine Zufallsaufgabe, das Gerät
unterschreibt sie mit seinem geheimen Schlüssel, der Server prüft die
Unterschrift gegen den hinterlegten öffentlichen Schlüssel. Es gibt nichts
abzufangen und nichts zu erraten.
"""

from __future__ import annotations

import base64
import json
import os
import secrets
import tempfile
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

ORDNER = Path.home() / ".hetzner-app"
GERAETE = ORDNER / "geraete.json"
SITZUNGEN = ORDNER / "anmeldungen.json"

# Wie lange eine Zufallsaufgabe gültig ist. Kurz, damit sie niemand
# aufheben und später wiederverwenden kann.
AUFGABE_GILT = 120          # Sekunden

# Wie lange man ohne neue Unterschrift angemeldet bleibt. Kürzer als früher
# (war ein Jahr) — ein abgegriffener Cookie ist damit nicht mehr ewig nutzbar.
# Wer die App regelmäßig benutzt, bleibt trotzdem angemeldet: Die Frist wird bei
# Nutzung stillschweigend wieder aufgefüllt (siehe anmeldung_benutzt).
ANMELDUNG_GILT = 60 * 60 * 24 * 90     # 90 Tage

# Schützt die Lese-ändern-Schreib-Zyklen der beiden JSON-Dateien. FastAPI führt
# synchrone Endpunkte im Threadpool aus — ohne diese Sperre könnten zwei
# gleichzeitige Anmeldungen einander überschreiben (eine frische Marke ginge
# verloren, das Gerät flöge sofort wieder raus).
_sperre = threading.Lock()


@dataclass
class Geraet:
    name: str
    schluessel: str          # öffentlicher Schlüssel, base64
    hinzugefuegt: int


# Offene Zufallsaufgaben. Nur im Arbeitsspeicher — nach einem Neustart des
# Dienstes muss man sich eben neu anmelden, das kostet einen Wimpernschlag.
_aufgaben: dict[str, float] = {}


# --- Geräte verwalten --------------------------------------------------------

def _laden() -> list[Geraet]:
    if not GERAETE.exists():
        return []
    try:
        return [Geraet(**g) for g in json.loads(GERAETE.read_text())]
    except (json.JSONDecodeError, OSError, TypeError):
        return []


def _atomar_schreiben(ziel: Path, text: str) -> None:
    """Schreibt eine Datei unteilbar — mit EIGENER Temp-Datei je Aufruf.

    Ein fester ".tmp"-Name (wie früher) wäre bei zwei gleichzeitigen Schreibern
    ein Datentopf für beide: Sie überschrieben dieselbe Temp-Datei und das
    Ergebnis konnte trotz des atomaren replace() beschädigt sein.
    """
    ORDNER.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=ORDNER, prefix=ziel.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(text)
        os.chmod(tmp, 0o600)
        os.replace(tmp, ziel)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _speichern(geraete: list[Geraet]) -> None:
    _atomar_schreiben(GERAETE, json.dumps([asdict(g) for g in geraete], indent=2))


def liste() -> list[Geraet]:
    return _laden()


def erlauben(name: str, schluessel: str) -> Geraet:
    """Ein Gerät freischalten. Wird von Hand aufgerufen, nie über das Netz —
    es gibt bewusst keine Tür, durch die sich jemand selbst eintragen kann."""
    schluessel = schluessel.strip()
    _pruefe_schluessel(schluessel)         # unbrauchbare Schlüssel gar nicht erst annehmen

    geraete = [g for g in _laden() if g.schluessel != schluessel]
    neu = Geraet(name=name, schluessel=schluessel, hinzugefuegt=int(time.time()))
    geraete.append(neu)
    _speichern(geraete)
    return neu


def entfernen(name: str) -> bool:
    """Ein verlorenes Handy aussperren — wirklich, samt laufender Anmeldung.

    Früher wurde nur der Schlüssel gelöscht: Das Gerät konnte sich zwar nicht
    mehr NEU anmelden, sein vorhandener Anmelde-Cookie galt aber weiter bis zu
    ein Jahr. Genau der versprochene Fall funktionierte also nicht. Jetzt fliegt
    mit dem Gerät auch jede Anmelde-Marke, die an es gebunden ist.
    """
    with _sperre:
        geraete = _laden()
        rest = [g for g in geraete if g.name != name]
        if len(rest) == len(geraete):
            return False
        _speichern(rest)

        # Marken dieses Geräts widerrufen — und dazu alle noch ungebundenen
        # (aus der Zeit vor dieser Änderung): Wessen sie sind, lässt sich nicht
        # mehr sagen, und beim Aussperren geht Sicherheit vor Bequemlichkeit.
        # Betroffen ist höchstens das eigene Gerät, das sich einmal neu anmeldet.
        werte = _anmeldungen()
        behalten = {
            m: e for m, e in werte.items()
            if _marke_geraet(e) not in (name, None)
        }
        if len(behalten) != len(werte):
            _anmeldungen_speichern(behalten)
    return True


def _pruefe_schluessel(schluessel: str) -> ec.EllipticCurvePublicKey:
    roh = base64.b64decode(schluessel, validate=True)
    key = serialization.load_der_public_key(roh)
    if not isinstance(key, ec.EllipticCurvePublicKey):
        raise ValueError("Das ist kein Schlüssel der erwarteten Art.")
    return key


# --- Anmelden ----------------------------------------------------------------

def aufgabe_stellen() -> str:
    """Eine Zufallsaufgabe, die das Gerät unterschreiben muss."""
    jetzt = time.time()
    # Abgelaufene wegräumen, damit sich hier nichts ansammelt.
    for alt in [a for a, frist in _aufgaben.items() if frist < jetzt]:
        _aufgaben.pop(alt, None)

    aufgabe = secrets.token_urlsafe(32)
    _aufgaben[aufgabe] = jetzt + AUFGABE_GILT
    return aufgabe


def unterschrift_pruefen(aufgabe: str, unterschrift: str) -> Geraet | None:
    """Wer hat unterschrieben? Gibt das Gerät zurück — oder None."""
    frist = _aufgaben.pop(aufgabe, None)   # jede Aufgabe gilt nur ein einziges Mal
    if frist is None or frist < time.time():
        return None

    try:
        roh = base64.b64decode(unterschrift, validate=True)
    except Exception:
        return None

    # Der Browser liefert die Unterschrift als zwei aneinandergehängte Zahlen;
    # die Krypto-Bibliothek erwartet sie anders verpackt.
    if len(roh) != 64:
        return None
    r = int.from_bytes(roh[:32], "big")
    s = int.from_bytes(roh[32:], "big")
    verpackt = utils.encode_dss_signature(r, s)

    for geraet in _laden():
        try:
            key = _pruefe_schluessel(geraet.schluessel)
            key.verify(verpackt, aufgabe.encode(), ec.ECDSA(hashes.SHA256()))
            return geraet
        except (InvalidSignature, ValueError):
            continue

    return None


# --- Angemeldet bleiben ------------------------------------------------------
#
# Nach erfolgreicher Unterschrift bekommt das Gerät ein Sitzungsplätzchen, damit
# es nicht bei jedem Klick neu unterschreiben muss.

# Eine Anmelde-Marke wird als {"geraet": name, "frist": zeit} gespeichert.
# Alte Stände hielten nur die nackte Frist als Zahl — beide Formen werden hier
# gelesen, damit niemand durch die Umstellung ausgesperrt wird. Eine solche
# Alt-Marke gilt weiter bis zum Ablauf, ist aber keinem Gerät zugeordnet.

def _marke_frist(eintrag: object) -> float:
    if isinstance(eintrag, dict):
        try:
            return float(eintrag.get("frist", 0))
        except (TypeError, ValueError):
            return 0.0
    try:
        return float(eintrag)      # altes Format: nackte Zahl
    except (TypeError, ValueError):
        return 0.0


def _marke_geraet(eintrag: object) -> str | None:
    return eintrag.get("geraet") if isinstance(eintrag, dict) else None


def _anmeldungen() -> dict[str, object]:
    if not SITZUNGEN.exists():
        return {}
    try:
        werte = json.loads(SITZUNGEN.read_text())
        return werte if isinstance(werte, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


def _anmeldungen_speichern(werte: dict[str, object]) -> None:
    _atomar_schreiben(SITZUNGEN, json.dumps(werte))


def anmeldung_ausstellen(geraet: str) -> str:
    """Eine neue Anmelde-Marke, fest an das unterschreibende Gerät gebunden."""
    marke = secrets.token_urlsafe(32)
    jetzt = time.time()
    with _sperre:
        werte = {m: e for m, e in _anmeldungen().items()
                 if _marke_frist(e) > jetzt}        # Abgelaufene raus
        werte[marke] = {"geraet": geraet, "frist": jetzt + ANMELDUNG_GILT}
        _anmeldungen_speichern(werte)
    return marke


def anmeldung_gueltig(marke: str) -> bool:
    if not marke:
        return False
    eintrag = _anmeldungen().get(marke)
    return eintrag is not None and _marke_frist(eintrag) > time.time()


def anmeldung_benutzt(marke: str) -> None:
    """Frist auffrischen, wenn die Marke schon über die Hälfte durch ist.

    So bleibt ein aktiver Nutzer angemeldet, obwohl die Grundlaufzeit kurz ist —
    ohne bei jedem einzelnen Klick in die Datei zu schreiben (nur einmal pro
    halber Laufzeit).
    """
    jetzt = time.time()
    with _sperre:
        werte = _anmeldungen()
        eintrag = werte.get(marke)
        if eintrag is None:
            return
        frist = _marke_frist(eintrag)
        if frist <= jetzt or frist - jetzt > ANMELDUNG_GILT / 2:
            return                              # abgelaufen oder noch frisch genug
        werte[marke] = {"geraet": _marke_geraet(eintrag),
                        "frist": jetzt + ANMELDUNG_GILT}
        _anmeldungen_speichern(werte)


def abmelden(marke: str) -> None:
    """Eine einzelne Anmeldung beenden (Logout auf diesem Gerät)."""
    if not marke:
        return
    with _sperre:
        werte = _anmeldungen()
        if marke in werte:
            del werte[marke]
            _anmeldungen_speichern(werte)
