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
import secrets
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
ANMELDUNG_GILT = 60 * 60 * 24 * 365


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


def _speichern(geraete: list[Geraet]) -> None:
    ORDNER.mkdir(parents=True, exist_ok=True)
    tmp = GERAETE.with_suffix(".tmp")
    tmp.write_text(json.dumps([asdict(g) for g in geraete], indent=2))
    tmp.chmod(0o600)
    tmp.replace(GERAETE)


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
    """Ein verlorenes Handy aussperren. Die anderen Geräte bleiben unberührt."""
    geraete = _laden()
    rest = [g for g in geraete if g.name != name]
    if len(rest) == len(geraete):
        return False
    _speichern(rest)
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

def _anmeldungen() -> dict[str, float]:
    if not SITZUNGEN.exists():
        return {}
    try:
        return json.loads(SITZUNGEN.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _anmeldungen_speichern(werte: dict[str, float]) -> None:
    ORDNER.mkdir(parents=True, exist_ok=True)
    tmp = SITZUNGEN.with_suffix(".tmp")
    tmp.write_text(json.dumps(werte))
    tmp.chmod(0o600)
    tmp.replace(SITZUNGEN)


def anmeldung_ausstellen() -> str:
    marke = secrets.token_urlsafe(32)
    werte = _anmeldungen()
    jetzt = time.time()
    werte = {m: f for m, f in werte.items() if f > jetzt}   # Abgelaufene raus
    werte[marke] = jetzt + ANMELDUNG_GILT
    _anmeldungen_speichern(werte)
    return marke


def anmeldung_gueltig(marke: str) -> bool:
    if not marke:
        return False
    frist = _anmeldungen().get(marke)
    return frist is not None and frist > time.time()
