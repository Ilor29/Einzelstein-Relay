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

# Eigene Sperre für die Aufgaben-Liste: Sie wird auch vom unangemeldeten
# /api/aufgabe angefasst, und FastAPI führt synchrone Endpunkte im Threadpool
# aus — ohne Sperre konnten zwei gleichzeitige Anmeldungen die Aufräum-Schleife
# und ein Einfügen verzahnen ("dictionary changed size during iteration" → 500).
_aufgaben_sperre = threading.Lock()

# Obergrenze gegen Flutung: /api/aufgabe ist der einzige unangemeldete
# Wachstumsweg. Ohne Deckel könnte ein Angreifer die Liste im 120-Sekunden-
# Fenster mit Millionen Einträgen füllen. Bei Überschreitung fliegen die
# ältesten heraus — ein ehrlicher Nutzer merkt davon nichts.
_AUFGABEN_MAX = 10_000


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
    """Ein Gerät freischalten — vom Server aus oder nach geprüftem Kopplungscode.

    Unter der Schreibsperre: Ohne sie konnten zwei gleichzeitige Eintragungen
    (Code-Weg und Erst-Besucher-Weg) einander überschreiben — im schlimmsten
    Fall löschte der Fremde das frisch gekoppelte Besitzer-Gerät (Fund der
    Code-Durchsicht 20.08.). Jede Eintragung schließt außerdem die
    Erst-Besucher-Tür endgültig (siehe _tuer_schliessen).
    """
    schluessel = schluessel.strip()
    _pruefe_schluessel(schluessel)         # unbrauchbare Schlüssel gar nicht erst annehmen

    with _sperre:
        geraete = [g for g in _laden() if g.schluessel != schluessel]
        neu = Geraet(name=name, schluessel=schluessel, hinzugefuegt=int(time.time()))
        geraete.append(neu)
        _speichern(geraete)
        _tuer_schliessen()
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


def schluessel_ok(schluessel: str) -> bool:
    """Ist das ein brauchbarer öffentlicher Schlüssel? (ohne Ausnahme)"""
    try:
        _pruefe_schluessel(schluessel.strip())
        return True
    except Exception:
        return False


# --- Kopplung: Selbstbedienungs-Freischaltung per Code -----------------------
#
# Der bisherige Weg — erlauben() nur vom Server aus — bleibt. Für einen
# Nicht-Techniker ist er aber eine Wand: Er müsste den öffentlichen Schlüssel
# vom Handy in eine Server-Kommandozeile tragen. Der Kopplungscode dreht das
# um: Der Server (setup.sh druckt ihn) ODER ein schon freigeschaltetes Gerät
# erzeugt einen kurzen Code, den man am Handy eintippt. Kein Schlüssel zum
# Kopieren, keine Kommandozeile.
#
# Sicher bleibt es, weil der Code ein Geheimnis ist, das nur sieht, wer den
# Server aufgesetzt hat oder schon ein Gerät drin hat — und weil er
#   * kurzlebig ist (15 Min),
#   * einmalig (nach erfolgreicher Kopplung verbraucht),
#   * gedrosselt (nach zu vielen Fehlversuchen kurze Sperre gegen Erraten).
# Ohne gültigen Code trägt sich niemand ein; die alte Zusicherung „nur wer
# schon Zugang hat, öffnet die Tür" bleibt gewahrt.

KOPPLUNG = ORDNER / "kopplung.json"
KOPPLUNG_GILT = 900          # Sekunden — 15 Minuten
# Ohne 0/O/1/I/L: am Handy und beim Vorlesen nicht zu verwechseln.
_KOPPEL_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
_KOPPEL_LAENGE = 8           # 32^8 ≈ 10^12 — mit Drossel praktisch nicht zu erraten

# Drossel gegen Erraten: höchstens so viele Fehlversuche im Fenster. Nur im
# Arbeitsspeicher — ein Dienst-Neustart hebt die Sperre auf, das ist in Ordnung.
_koppel_fehlversuche: list[float] = []
_KOPPEL_MAX = 20
_KOPPEL_FENSTER = 300        # 5 Minuten


def _kopplung_speichern(stand: dict | None) -> None:
    if stand is None:
        try:
            KOPPLUNG.unlink()
        except FileNotFoundError:
            pass
        return
    _atomar_schreiben(KOPPLUNG, json.dumps(stand))


def _kopplung_laden() -> dict | None:
    try:
        stand = json.loads(KOPPLUNG.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return stand if isinstance(stand, dict) else None


def _kopplung_formatieren(code: str) -> str:
    # In der Mitte geteilt, leichter abzulesen und vorzulesen: ABCD-EFGH.
    h = len(code) // 2
    return f"{code[:h]}-{code[h:]}"


def kopplung_neu(gueltig: int = KOPPLUNG_GILT) -> str:
    """Einen frischen Kopplungscode erzeugen, ablegen, formatiert zurückgeben.

    Ersetzt einen etwaigen alten — es gibt immer nur einen gültigen Code.
    """
    code = "".join(secrets.choice(_KOPPEL_ALPHABET) for _ in range(_KOPPEL_LAENGE))
    with _sperre:
        _kopplung_speichern({"code": code, "frist": time.time() + gueltig})
    return _kopplung_formatieren(code)


def _kopplung_saeubern(eingabe: str) -> str:
    """Tippfehler-tolerant: Groß, ohne Bindestrich/Leerzeichen, nur gültige Zeichen."""
    return "".join(c for c in eingabe.upper() if c in _KOPPEL_ALPHABET)


def kopplung_pruefen_und_verbrauchen(eingabe: str) -> bool:
    """Stimmt der eingetippte Code? Bei Erfolg wird er verbraucht (einmalig)."""
    sauber = _kopplung_saeubern(eingabe or "")
    jetzt = time.time()
    with _sperre:
        _koppel_fehlversuche[:] = [t for t in _koppel_fehlversuche if t > jetzt - _KOPPEL_FENSTER]
        if len(_koppel_fehlversuche) >= _KOPPEL_MAX:
            return False                        # zu viele Fehlversuche — kurz gesperrt
        stand = _kopplung_laden()
        gueltig = (
            stand is not None
            and len(sauber) == _KOPPEL_LAENGE
            and float(stand.get("frist", 0)) > jetzt
            and secrets.compare_digest(sauber, str(stand.get("code", "")))
        )
        if gueltig:
            _kopplung_speichern(None)           # verbraucht
            _koppel_fehlversuche.clear()
            return True
        _koppel_fehlversuche.append(jetzt)
        return False


# --- Erst-Besucher-Kopplung ----------------------------------------------------
#
# Ein frisch aufgesetzter Server gehört noch niemandem — und sein Besitzer hat
# kein Terminal, um an einen Code zu kommen (der aus der Einrichtung lebt nur
# 15 Minuten). Darum: Solange NULL Geräte eingetragen sind UND der Server jung
# ist, darf sich das erste Handy ohne Code eintragen. Jede Eintragung schließt
# die Tür endgültig; nach Ablauf des Fensters gilt nur noch der Code-Weg.
#
# Bewusst getragenes Restrisiko (CODE-GUARD-Bericht-Erstkopplung.md): Im
# offenen Fenster könnte ein Fremder den LEEREN Server übernehmen — der
# Besitzer merkt es sofort (er kommt nicht rein), Daten liegen keine drauf.
# Mittelfristige Schließung: Kopplungswort im Cloud-Init-Text.

ERSTSTART = ORDNER / "erststart"
# Der endgültige Riegel. „Geräteliste gerade leer" war als Tür-Kriterium zu
# schwach (Fund der Code-Durchsicht 20.08.): Sperrt jemand sein einziges Gerät
# aus oder ist geraete.json einmal unlesbar, stünde die Tür im 24-h-Fenster
# wieder offen. Darum schließt die ERSTE erfolgreiche Eintragung die Tür über
# diese Datei — dauerhaft, unabhängig vom späteren Inhalt der Geräteliste.
ERSTKOPPLUNG_ZU = ORDNER / "erstkopplung-zu"
ERSTKOPPLUNG_FENSTER = int(os.environ.get("HETZNER_ERSTKOPPLUNG_STUNDEN", "24")) * 3600


def _tuer_schliessen() -> None:
    """Die Erst-Besucher-Tür endgültig verriegeln (Aufruf unter _sperre)."""
    if not ERSTKOPPLUNG_ZU.exists():
        _atomar_schreiben(ERSTKOPPLUNG_ZU, str(int(time.time())))


def erststart_merken() -> None:
    """Beim Dienststart einmalig festhalten, wann dieser Server geboren wurde.

    Auf bestehenden Installationen entsteht der Stempel erst mit diesem
    Update — dort sind aber längst Geräte eingetragen, also wird die Tür
    sofort mitverriegelt, statt nachträglich ein 24-h-Fenster zu öffnen.
    """
    with _sperre:
        if not ERSTSTART.exists():
            _atomar_schreiben(ERSTSTART, str(int(time.time())))
        if _laden():
            _tuer_schliessen()


def _erststart() -> float:
    try:
        return float(ERSTSTART.read_text().strip())
    except (FileNotFoundError, ValueError, OSError):
        return 0.0


def erstkopplung_offen() -> bool:
    """Darf sich das allererste Gerät noch ohne Code eintragen?"""
    if ERSTKOPPLUNG_ZU.exists() or _laden():
        return False
    geburt = _erststart()
    return geburt > 0 and (time.time() - geburt) < ERSTKOPPLUNG_FENSTER


def erstkopplung_versuchen(name: str, schluessel: str) -> Geraet | None:
    """Das allererste Gerät eintragen — atomar, nur wenn wirklich keines da ist.

    Leerheit wird ERST im gesperrten Block geprüft: Zwei gleichzeitige „Erste"
    dürfen nicht beide gewinnen — der zweite bekommt None.
    """
    schluessel = schluessel.strip()
    _pruefe_schluessel(schluessel)
    with _sperre:
        if not erstkopplung_offen():
            return None
        neu = Geraet(name=name, schluessel=schluessel, hinzugefuegt=int(time.time()))
        _speichern([neu])
        _tuer_schliessen()
    print(f"Erst-Besucher-Kopplung: Gerät „{name}“ eingetragen — die Tür ist jetzt zu.",
          flush=True)
    return neu


# --- Anmelden ----------------------------------------------------------------

def aufgabe_stellen() -> str:
    """Eine Zufallsaufgabe, die das Gerät unterschreiben muss."""
    jetzt = time.time()
    aufgabe = secrets.token_urlsafe(32)
    with _aufgaben_sperre:
        # Abgelaufene wegräumen, damit sich hier nichts ansammelt.
        for alt in [a for a, frist in _aufgaben.items() if frist < jetzt]:
            _aufgaben.pop(alt, None)
        # Notbremse gegen Flutung: bleibt es trotzdem zu voll, die ältesten raus.
        if len(_aufgaben) >= _AUFGABEN_MAX:
            zu_alt = sorted(_aufgaben, key=_aufgaben.get)[: len(_aufgaben) - _AUFGABEN_MAX + 1]
            for a in zu_alt:
                _aufgaben.pop(a, None)
        _aufgaben[aufgabe] = jetzt + AUFGABE_GILT
    return aufgabe


def unterschrift_pruefen(aufgabe: str, unterschrift: str) -> Geraet | None:
    """Wer hat unterschrieben? Gibt das Gerät zurück — oder None."""
    with _aufgaben_sperre:
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
