"""Benachrichtigungen — damit du nicht nachschauen musst.

Der Server behält die Sitzungen im Auge. Sobald eine von "arbeitet" auf
"wartet auf dich" oder "fertig" springt, klingelt dein Handy. Das geht auch,
wenn die App geschlossen ist — dafür sorgt der Service Worker.

Die Nachrichten laufen über den Push-Dienst des Browsers (bei Android also
Google). Der sieht allerdings nichts: Der Inhalt ist verschlüsselt, und nur
dein Handy hat den Schlüssel dafür.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pywebpush import WebPushException, webpush

from . import state

ORDNER = Path.home() / ".hetzner-app"
VAPID = ORDNER / "vapid.json"
EMPFAENGER = ORDNER / "empfaenger.json"

# Wie oft wir nachsehen. Zehn Sekunden sind genug — schneller merkt man den
# Unterschied ohnehin nicht, und es kostet fast nichts.
TAKT = 10


# --- Der Ausweis des Servers gegenüber dem Push-Dienst ------------------------

def _vapid() -> dict:
    """Erzeugt einmalig ein Schlüsselpaar, mit dem sich der Server ausweist."""
    if VAPID.exists():
        return json.loads(VAPID.read_text())

    privat = ec.generate_private_key(ec.SECP256R1())

    # Der private Schlüssel als base64url-kodiertes DER.
    #
    # Nicht als PEM: pywebpush schiebt den String ungefragt durch eine
    # base64-Entzifferung, und ein PEM-Text zerfällt dabei zu Unsinn — die
    # Probenachricht scheiterte mit "Could not deserialize key data".
    der = privat.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    pem = base64.urlsafe_b64encode(der).decode().rstrip("=")

    # Der öffentliche Schlüssel, wie der Browser ihn erwartet: die rohen
    # Punktkoordinaten, base64-kodiert ohne Füllzeichen.
    roh = privat.public_key().public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )
    oeffentlich = base64.urlsafe_b64encode(roh).decode().rstrip("=")

    werte = {"privat": pem, "oeffentlich": oeffentlich}
    ORDNER.mkdir(parents=True, exist_ok=True)
    VAPID.write_text(json.dumps(werte))
    VAPID.chmod(0o600)
    return werte


def oeffentlicher_schluessel() -> str:
    return _vapid()["oeffentlich"]


# --- Wer benachrichtigt werden will ------------------------------------------

def _empfaenger() -> list[dict]:
    if not EMPFAENGER.exists():
        return []
    try:
        return json.loads(EMPFAENGER.read_text())
    except (json.JSONDecodeError, OSError):
        return []


def _empfaenger_speichern(liste: list[dict]) -> None:
    ORDNER.mkdir(parents=True, exist_ok=True)
    EMPFAENGER.write_text(json.dumps(liste, indent=2))
    EMPFAENGER.chmod(0o600)


def eintragen(anmeldung: dict) -> None:
    """Ein Gerät will benachrichtigt werden."""
    liste = [e for e in _empfaenger() if e.get("endpoint") != anmeldung.get("endpoint")]
    liste.append(anmeldung)
    _empfaenger_speichern(liste)


def austragen(endpoint: str) -> None:
    _empfaenger_speichern([e for e in _empfaenger() if e.get("endpoint") != endpoint])


# --- Schicken ----------------------------------------------------------------

def schicken(titel: str, text: str, sitzung: str = "") -> int:
    """Schickt die Nachricht an alle eingetragenen Geräte."""
    werte = _vapid()
    nachricht = json.dumps({"titel": titel, "text": text, "sitzung": sitzung})

    zugestellt = 0
    tot: list[str] = []

    for empfaenger in _empfaenger():
        try:
            webpush(
                subscription_info=empfaenger,
                data=nachricht,
                vapid_private_key=werte["privat"],
                # Der Push-Dienst will wissen, wen er bei Ärger anschreiben kann.
                vapid_claims={"sub": "mailto:mixkultur@googlemail.com"},
                ttl=600,
            )
            zugestellt += 1
        except WebPushException as fehler:
            # 404 und 410 heißen: Dieses Gerät gibt es nicht mehr. Dann tragen
            # wir es aus, statt es ewig weiter anzuschreiben.
            if fehler.response is not None and fehler.response.status_code in (404, 410):
                tot.append(empfaenger.get("endpoint", ""))

    for endpoint in tot:
        austragen(endpoint)

    return zugestellt


# --- Der Wächter -------------------------------------------------------------
#
# Er merkt sich, in welchem Zustand jede Sitzung zuletzt war, und schlägt an,
# wenn sie aufhört zu arbeiten.

_zuletzt: dict[str, str] = {}


def _pruefen() -> None:
    for sitzung in state.overview():
        name = sitzung["name"]
        jetzt = sitzung["state"]
        vorher = _zuletzt.get(name)
        _zuletzt[name] = jetzt

        # Beim ersten Durchlauf kennen wir den vorherigen Zustand nicht — dann
        # gäbe es sofort eine Nachricht für jede ruhende Sitzung. Also still.
        if vorher is None or vorher != state.RUNNING:
            continue
        if not sitzung["notifyWhenDone"]:
            continue

        if jetzt == state.WAITING:
            schicken(
                f"{name} wartet auf dich",
                sitzung["preview"] or "Claude hat eine Rückfrage.",
                name,
            )
        elif jetzt == state.IDLE:
            schicken(
                f"{name} ist fertig",
                sitzung["preview"] or "Claude ist durch.",
                name,
            )

    # Sitzungen, die es nicht mehr gibt, vergessen.
    lebende = {s["name"] for s in state.overview()}
    for name in [n for n in _zuletzt if n not in lebende]:
        _zuletzt.pop(name, None)


async def waechter() -> None:
    """Läuft, solange der Dienst läuft."""
    while True:
        try:
            await asyncio.to_thread(_pruefen)
        except Exception:
            # Ein Fehler beim Nachsehen darf niemals den Dienst umbringen.
            pass
        await asyncio.sleep(TAKT)
