"""Zurückspulen (/rewind) vom Handy aus (Monitor-Baustein 5).

Claude Code zeigt bei /rewind eine Auswahl im Terminal: erst die eigenen
Nachrichten zur Wahl, dann eine Bestätigung mit nummerierten Möglichkeiten.
Dieses Modul liest beide Bildschirme als Text. Das Tippen übernimmt der Server
(tmux.send_key), hier steht nur das Lesen, damit es sich ohne Sitzung testen lässt.
"""
from __future__ import annotations

import re

_LISTE_KOPF = "point before"          # „Restore the code and/or conversation to the point before…“
_LISTE_FUSS = "enter to continue"
_BESTAETIGUNG = "confirm you want to restore"
_OPTION = re.compile(r"^\s*(?:❯\s*)?(\d)\.\s+(\S.*?)\s*$")

# Die Wörter der Möglichkeiten, wie Claude Code sie nennt, auf Deutsch.
_UEBERSETZUNG = [
    ("restore code and conversation", "Code und Gespräch zurücksetzen"),
    ("restore conversation", "Nur das Gespräch zurücksetzen"),
    ("restore code", "Nur den Code zurücksetzen"),
    ("summarize from here", "Ab hier zusammenfassen"),
    ("summarize up to here", "Bis hier zusammenfassen"),
    ("never mind", "Doch nicht, nichts ändern"),
]


def ist_auswahl(schirm: str) -> bool:
    unten = "\n".join(schirm.rstrip().splitlines()[-30:]).lower()
    return "rewind" in unten and _LISTE_KOPF in unten and _LISTE_FUSS in unten


def ist_bestaetigung(schirm: str) -> bool:
    unten = "\n".join(schirm.rstrip().splitlines()[-30:]).lower()
    return _BESTAETIGUNG in unten


def eintraege(schirm: str) -> list[dict]:
    """Die wählbaren Nachrichten, ältere zuerst. Der Eintrag „(current)“ zählt nicht."""
    zeilen = schirm.rstrip().splitlines()
    start = None
    for i in range(len(zeilen) - 1, -1, -1):
        if _LISTE_KOPF in zeilen[i].lower() and "restore" in zeilen[i].lower():
            start = i + 1
            break
    if start is None:
        return []
    texte = []
    for z in zeilen[start:]:
        if _LISTE_FUSS in z.lower():
            break
        t = z.strip()
        if t.startswith("❯"):
            t = t[1:].strip()
        if not t:
            continue
        if t.lower() == "(current)":
            break
        texte.append(t)
    # Je Nachricht eine Zeile Text und eine Zeile zu den Änderungen am Code.
    ergebnis = []
    for i in range(0, len(texte) - 1, 2):
        ergebnis.append({"text": texte[i], "aenderung": texte[i + 1]})
    return ergebnis


def optionen(schirm: str) -> list[dict]:
    """Die nummerierten Möglichkeiten der Bestätigung, mit deutscher Bezeichnung."""
    unten = schirm.rstrip().splitlines()[-14:]
    gefunden = []
    for z in unten:
        m = _OPTION.match(z)
        if m:
            roh = m.group(2)
            deutsch = next((d for k, d in _UEBERSETZUNG if roh.lower().startswith(k)), roh)
            gefunden.append({"nr": int(m.group(1)), "text": deutsch, "original": roh})
    return gefunden


def zitierte_nachricht(schirm: str) -> str:
    """Die Nachricht im Kasten der Bestätigung (Zeilen mit │)."""
    teile = []
    for z in schirm.splitlines():
        s = z.strip()
        if s.startswith("│"):
            t = s.lstrip("│").strip()
            if t and not re.match(r"^\(\d+\w* ago\)$", t):
                teile.append(t)
    return " ".join(teile)


def eingabe_text(schirm: str) -> str:
    """Was in der Eingabezeile steht (die unterste Zeile mit ❯). Leer heißt: nichts."""
    for z in reversed(schirm.rstrip().splitlines()):
        t = z.strip()
        if t.startswith("❯"):
            return t[1:].strip()
    return ""
