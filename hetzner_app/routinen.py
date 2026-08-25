"""Die Routinen — was auf dem Server von selbst läuft.

Der Server läuft rund um die Uhr, und mit der Zeit sammeln sich Dinge an, die
er ohne dich tut: der nächtliche Recherche-Lauf, der Speicher-Wächter, die
Sicherung alle zehn Minuten. Bisher standen die nur in der crontab und in
systemd-Timern — vom Handy aus unsichtbar. Man wusste nicht, was wann läuft,
ob es zuletzt gelaufen ist, und anhalten konnte man es erst recht nicht.

Dieses Modul liest beides zusammen und macht daraus eine Liste für die App:
Name, wofür es gut ist (aus dem Kopf-Kommentar des Skripts), der Zeitplan in
Worten, wann es zuletzt lief und wann es wieder dran ist. Cron-Einträge lassen
sich außerdem pausieren (wir kommentieren die Zeile aus, mit einer eigenen
Marke, damit wir sie wiederfinden) und von Hand anstoßen. Die systemd-Timer
zeigen wir nur an — die gehören root, und root spielen wir hier nicht.

Was von Hand angestoßen wird, ist immer ein Befehl, der schon in der crontab
steht. Die App kann keinen eigenen Befehl mitschicken — sie nennt nur die
Kennung einer Zeile, die wir selbst gelesen haben.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

ORDNER = Path.home() / ".hetzner-app" / "routinen"
LAEUFE = ORDNER / "laeufe.json"

# Die Marke, mit der wir eine pausierte Zeile in der crontab auskommentieren.
PAUSE_MARKE = "#[pausiert] "

# Läuft gerade etwas, das wir von Hand gestartet haben? Kennung → Popen.
_laufend: dict[str, subprocess.Popen] = {}

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag",
              "Samstag", "Sonntag"]


# --- crontab lesen und schreiben ---------------------------------------------

def _crontab_lesen() -> list[str]:
    try:
        aus = subprocess.run(["crontab", "-l"], capture_output=True, text=True,
                             timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return []
    if aus.returncode != 0:
        return []
    return aus.stdout.splitlines()


def _crontab_schreiben(zeilen: list[str]) -> None:
    text = "\n".join(zeilen) + "\n"
    subprocess.run(["crontab", "-"], input=text, text=True, timeout=5,
                   check=True)


def _kennung(befehl: str) -> str:
    """Kurze, stabile Kennung einer Cron-Zeile — hängt nur am Befehl, nicht am
    Zeitplan und nicht daran, ob sie gerade pausiert ist."""
    return hashlib.sha1(befehl.strip().encode()).hexdigest()[:10]


def _zeile_zerlegen(zeile: str) -> tuple[str, str, bool] | None:
    """Aus einer crontab-Zeile (zeitplan, befehl, pausiert) — oder None, wenn
    die Zeile kein Zeitplan ist (leer, Kommentar, Variable, @reboot)."""
    pausiert = False
    if zeile.startswith(PAUSE_MARKE):
        zeile = zeile[len(PAUSE_MARKE):]
        pausiert = True
    zeile = zeile.strip()
    if not zeile or zeile.startswith("#"):
        return None
    if zeile.startswith("@"):
        # @reboot & Co. sind Dienste, die beim Start hochkommen — keine Routine.
        return None
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", zeile):
        return None
    teile = zeile.split(None, 5)
    if len(teile) < 6:
        return None
    return " ".join(teile[:5]), teile[5], pausiert


# --- Zeitplan in Worten und nächster Lauf ------------------------------------

def _uhr(minute: str, stunde: str) -> str | None:
    if minute.isdigit() and stunde.isdigit():
        return f"{int(stunde)}:{int(minute):02d} Uhr"
    return None


def zeitplan_in_worten(ausdruck: str) -> str:
    """Die gängigen Muster in Alltagsdeutsch; alles andere bleibt roh stehen."""
    teile = ausdruck.split()
    if len(teile) != 5:
        return ausdruck
    minute, stunde, tag, monat, wochentag = teile

    m_alle = re.fullmatch(r"\*/(\d+)", minute)
    if m_alle and tag == "*" and monat == "*" and wochentag == "*":
        n = int(m_alle.group(1))
        takt = "jede Minute" if n == 1 else f"alle {n} Minuten"
        if stunde == "*":
            return takt
        h = re.fullmatch(r"(\d+)-(\d+)", stunde)
        if h:
            return f"{takt}, {h.group(1)} bis {h.group(2)} Uhr"
        return f"{takt} ({stunde} Uhr)"

    if minute.isdigit() and stunde == "*" and tag == "*" and monat == "*" \
            and wochentag == "*":
        return "stündlich" if minute == "0" else f"stündlich um Minute {int(minute)}"

    zeit = _uhr(minute, stunde)
    if zeit and monat == "*":
        if tag == "*" and wochentag == "*":
            return f"täglich um {zeit}"
        if tag == "*" and wochentag in ("1-5", "1,2,3,4,5"):
            return f"werktags um {zeit}"
        if tag == "*" and wochentag.isdigit():
            w = int(wochentag) % 7
            name = WOCHENTAGE[(w - 1) % 7]
            return f"jeden {name} um {zeit}"
        if tag.isdigit() and wochentag == "*":
            return f"am {int(tag)}. jedes Monats um {zeit}"
    return ausdruck


def _feld_passt(feld: str, wert: int, von: int, bis: int) -> bool:
    for stueck in feld.split(","):
        schritt = 1
        if "/" in stueck:
            stueck, s = stueck.split("/", 1)
            if not s.isdigit():
                return False
            schritt = int(s)
        if stueck == "*":
            lo, hi = von, bis
        elif "-" in stueck:
            a, b = stueck.split("-", 1)
            if not (a.isdigit() and b.isdigit()):
                return False
            lo, hi = int(a), int(b)
        elif stueck.isdigit():
            lo = hi = int(stueck)
        else:
            return False
        if lo <= wert <= hi and (wert - lo) % schritt == 0:
            return True
    return False


def naechster_lauf(ausdruck: str, ab: datetime | None = None) -> float | None:
    """Der nächste Zeitpunkt, an dem der Ausdruck greift — als Unix-Sekunden.
    Minute für Minute vorwärts geprüft, höchstens ein Jahr weit."""
    teile = ausdruck.split()
    if len(teile) != 5:
        return None
    minute, stunde, tag, monat, wochentag = teile
    t = (ab or datetime.now()).replace(second=0, microsecond=0) + timedelta(minutes=1)
    grenze = t + timedelta(days=366)
    while t < grenze:
        if not _feld_passt(stunde, t.hour, 0, 23):
            # Sprünge sparen: passt die Stunde nicht, gleich zur nächsten.
            t = t.replace(minute=0) + timedelta(hours=1)
            continue
        if (_feld_passt(monat, t.month, 1, 12)
                and _feld_passt(minute, t.minute, 0, 59)):
            # Cron: Wochentag 0 und 7 sind beide Sonntag; Python: Montag = 0.
            cron_wt = (t.weekday() + 1) % 7
            tag_ok = _feld_passt(tag, t.day, 1, 31)
            wt_ok = _feld_passt(wochentag, cron_wt, 0, 7) or (
                cron_wt == 0 and _feld_passt(wochentag, 7, 0, 7))
            # Tag und Wochentag: sind beide gesetzt, reicht Cron eines davon.
            if tag != "*" and wochentag != "*":
                passt = tag_ok or wt_ok
            elif tag != "*":
                passt = tag_ok
            elif wochentag != "*":
                passt = wt_ok
            else:
                passt = True
            if passt:
                return t.timestamp()
        t += timedelta(minutes=1)
    return None


# --- Was das Skript über sich selbst sagt ------------------------------------

def _skriptpfad(befehl: str) -> Path | None:
    """Der erste Pfad im Befehl, der auf eine Datei zeigt (.sh, .py …)."""
    for token in befehl.split():
        token = token.strip("'\"")
        if token.startswith("/") or token.startswith("~"):
            p = Path(os.path.expanduser(token))
            if p.is_file() and p.suffix in (".sh", ".py", ".bash"):
                return p
    return None


def _name_aus(pfad: Path | None, befehl: str) -> str:
    if pfad is None:
        return befehl[:40]
    roh = pfad.stem
    roh = re.sub(r"[-_]lauf$", "", roh)
    roh = roh.lstrip(".")
    woerter = re.split(r"[-_]+", roh)
    return " ".join(w[:1].upper() + w[1:] for w in woerter if w)


def _projekt_aus(pfad: Path | None) -> str:
    if pfad is None:
        return ""
    teile = pfad.parts
    if "projekte" in teile:
        i = teile.index("projekte")
        if i + 1 < len(teile) - 1:
            return teile[i + 1]
    return "Server"


def _beschreibung_aus(pfad: Path | None) -> tuple[str, str | None]:
    """Der Kopf-Kommentar des Skripts als Beschreibung, dazu ein Log-Pfad,
    falls er dort genannt wird („Log: ~/logs/…")."""
    if pfad is None:
        return "", None
    try:
        zeilen = pfad.read_text(errors="replace").splitlines()[:40]
    except OSError:
        return "", None
    saetze: list[str] = []
    in_docstring = False
    for z in zeilen:
        s = z.strip()
        if s.startswith("#!"):
            continue
        if s.startswith('"""'):
            if in_docstring:
                break
            in_docstring = True
            s = s[3:].strip()
            if s.endswith('"""'):
                saetze.append(s[:-3].strip())
                break
            if s:
                saetze.append(s)
            continue
        if in_docstring:
            if s.endswith('"""'):
                saetze.append(s[:-3].strip())
                break
            if not s:
                break        # erster Absatz reicht
            saetze.append(s)
            continue
        if s.startswith("#"):
            saetze.append(s.lstrip("#").strip())
            continue
        if saetze:
            break            # der Kommentarblock ist zu Ende
        if s == "":
            continue
        break
    text = " ".join(s for s in saetze if s)
    log = None
    m = re.search(r"Log:\s*(\S+)", text)
    if m:
        log = m.group(1).rstrip(".,")
        text = text[:m.start()].strip()
    # Hinweise, wann es läuft, sagen wir selbst — die brauchen wir hier nicht.
    text = re.sub(r"\s*(Wird|Läuft)[^.]*per Cron[^.]*\.", "", text).strip()
    return text[:320], log


def _log_aus(befehl: str, kopf_log: str | None) -> Path | None:
    m = re.search(r">>?\s*(\S+)", befehl)
    if m and not m.group(1).startswith("/dev/"):
        return Path(os.path.expanduser(m.group(1)))
    if kopf_log:
        return Path(os.path.expanduser(kopf_log))
    return None


# --- Läufe von Hand ----------------------------------------------------------

def _laeufe_lesen() -> dict:
    try:
        return json.loads(LAEUFE.read_text())
    except (OSError, ValueError):
        return {}


def _laeufe_schreiben(daten: dict) -> None:
    ORDNER.mkdir(parents=True, exist_ok=True)
    tmp = LAEUFE.with_suffix(".tmp")
    tmp.write_text(json.dumps(daten))
    os.replace(tmp, LAEUFE)


def _laufende_pruefen() -> None:
    """Fertige Hand-Läufe ins Lauf-Buch übertragen."""
    fertig = [k for k, p in _laufend.items() if p.poll() is not None]
    if not fertig:
        return
    daten = _laeufe_lesen()
    for k in fertig:
        p = _laufend.pop(k)
        eintrag = daten.get(k, {})
        eintrag["ende"] = time.time()
        eintrag["rc"] = p.returncode
        daten[k] = eintrag
    _laeufe_schreiben(daten)


def jetzt_ausfuehren(kennung: str) -> dict:
    """Eine Cron-Zeile sofort starten — egal ob pausiert. Läuft im Hintergrund;
    was sie ausgibt, landet in unserem eigenen Lauf-Protokoll."""
    _laufende_pruefen()
    if kennung in _laufend:
        raise ValueError("Diese Routine läuft gerade schon.")
    for zeile in _crontab_lesen():
        z = _zeile_zerlegen(zeile)
        if z and _kennung(z[1]) == kennung:
            befehl = z[1]
            break
    else:
        raise KeyError("Diese Routine gibt es nicht (mehr).")
    # Schickt die Zeile ihre Ausgabe ins Nichts („> /dev/null 2>&1"), nehmen
    # wir das für den Hand-Lauf weg — sonst bliebe unser Protokoll leer, und
    # genau das will man nach „Jetzt" sehen.
    befehl = re.sub(r"\s*>>?\s*/dev/null(\s+2>&1)?\s*$", "", befehl)
    ORDNER.mkdir(parents=True, exist_ok=True)
    log = ORDNER / f"{kennung}.log"
    with open(log, "w") as f:
        f.write(f"# Von Hand gestartet {datetime.now():%d.%m.%Y %H:%M:%S}\n")
        f.write(f"# {befehl}\n\n")
        f.flush()
        p = subprocess.Popen(
            ["/bin/bash", "-lc", befehl],
            cwd=str(Path.home()), stdout=f, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )
    _laufend[kennung] = p
    daten = _laeufe_lesen()
    daten[kennung] = {"start": time.time()}
    _laeufe_schreiben(daten)
    return {"ok": True}


def pausieren(kennung: str, pause: bool) -> dict:
    zeilen = _crontab_lesen()
    neu: list[str] = []
    gefunden = False
    for zeile in zeilen:
        z = _zeile_zerlegen(zeile)
        if z and _kennung(z[1]) == kennung:
            gefunden = True
            kern = zeile[len(PAUSE_MARKE):] if zeile.startswith(PAUSE_MARKE) else zeile
            neu.append((PAUSE_MARKE + kern) if pause else kern)
        else:
            neu.append(zeile)
    if not gefunden:
        raise KeyError("Diese Routine gibt es nicht (mehr).")
    _crontab_schreiben(neu)
    return {"ok": True, "pausiert": pause}


def protokoll(kennung: str, zeilen: int = 150) -> dict:
    """Die letzten Zeilen dessen, was die Routine geschrieben hat: erst ihr
    eigenes Log (wenn wir eines kennen), sonst unser Lauf-Protokoll."""
    for r in lesen():
        if r["id"] == kennung:
            break
    else:
        raise KeyError("Diese Routine gibt es nicht (mehr).")
    kandidaten = []
    if r.get("log"):
        kandidaten.append(Path(r["log"]))
    kandidaten.append(ORDNER / f"{kennung}.log")
    for pfad in kandidaten:
        try:
            if not pfad.is_file():
                continue
            with open(pfad, "rb") as f:
                f.seek(0, os.SEEK_END)
                groesse = f.tell()
                f.seek(max(0, groesse - 64_000))
                text = f.read().decode(errors="replace")
            letzte = text.splitlines()[-zeilen:]
            return {"quelle": str(pfad), "text": "\n".join(letzte)}
        except OSError:
            continue
    return {"quelle": "", "text": ""}


# --- systemd-Timer (nur lesen) ----------------------------------------------

def _timer_lesen() -> list[dict]:
    try:
        aus = subprocess.run(
            ["systemctl", "list-timers", "--all", "--no-pager", "-o", "json"],
            capture_output=True, text=True, timeout=5)
        timer = json.loads(aus.stdout or "[]")
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return []
    heim = str(Path.home())
    ich = os.environ.get("USER") or Path.home().name
    ergebnis = []
    for t in timer:
        dienst = t.get("activates") or ""
        einheit = t.get("unit") or ""
        if not dienst:
            continue
        try:
            show = subprocess.run(
                ["systemctl", "show", "-p", "ExecStart", "-p", "Description",
                 "-p", "User", "-p", "WorkingDirectory", dienst],
                capture_output=True, text=True, timeout=5).stdout
            tshow = subprocess.run(
                ["systemctl", "show", "-p", "TimersCalendar",
                 "-p", "TimersMonotonic", einheit],
                capture_output=True, text=True, timeout=5).stdout
        except (OSError, subprocess.TimeoutExpired):
            continue
        exec_ = ""
        beschreibung = ""
        nutzer = ""
        arbeitsordner = ""
        for z in show.splitlines():
            if z.startswith("ExecStart="):
                exec_ = z
            elif z.startswith("Description="):
                beschreibung = z[len("Description="):]
            elif z.startswith("User="):
                nutzer = z[len("User="):]
            elif z.startswith("WorkingDirectory="):
                arbeitsordner = z[len("WorkingDirectory="):]
        # Nur, was zu diesem Konto gehört — die Systemwartung von Ubuntu
        # (apt, logrotate, fstrim …) ist keine Routine von dir, und die
        # Wächter der Nachbarkonten gehen dich nichts an.
        if not (heim in exec_ or heim in arbeitsordner or nutzer == ich):
            continue
        m = re.search(r"argv\[\]=([^;]+);", exec_)
        befehl = (m.group(1).strip() if m else exec_)
        plan = ""
        m = re.search(r"OnCalendar=([^;]+)", tshow)
        if m:
            roh = m.group(1).strip()
            mm = re.fullmatch(r"\*-\*-\* (\d\d):(\d\d):\d\d", roh)
            plan = f"täglich um {int(mm.group(1))}:{mm.group(2)} Uhr" if mm else roh
        m = re.search(r"OnUnitActiveUSec=([^;]+)", tshow) or \
            re.search(r"OnUnitInactiveUSec=([^;]+)", tshow)
        if m and not plan:
            roh = m.group(1).strip()
            mm = re.fullmatch(r"(\d+)min", roh)
            plan = f"alle {mm.group(1)} Minuten" if mm else f"alle {roh}"
        naechster = (t.get("next") or 0) / 1_000_000 or None
        letzter = (t.get("last") or 0) / 1_000_000 or None
        pfad = _skriptpfad(befehl)
        ergebnis.append({
            "id": "t-" + re.sub(r"[^a-z0-9]+", "-", einheit.lower()),
            "quelle": "timer",
            "name": beschreibung or _name_aus(pfad, befehl),
            "projekt": _projekt_aus(pfad),
            "beschreibung": "",
            "befehl": befehl,
            "zeitplan": plan,
            "naechster": naechster,
            "letzter": letzter,
            "pausiert": False,
            "laeuft": False,
            "log": None,
            "einheit": einheit,
        })
    return ergebnis


# --- Die Liste für die App ---------------------------------------------------

def lesen() -> list[dict]:
    _laufende_pruefen()
    laeufe = _laeufe_lesen()
    ergebnis = []
    eintraege = []
    for zeile in _crontab_lesen():
        z = _zeile_zerlegen(zeile)
        if not z:
            continue
        plan, befehl, pausiert = z
        pfad = _skriptpfad(befehl)
        beschreibung, kopf_log = _beschreibung_aus(pfad)
        eintraege.append((plan, befehl, pausiert, pfad, beschreibung,
                          _log_aus(befehl, kopf_log)))
    # Teilen sich mehrere Routinen ein Log (die Skillkontor-Läufe schreiben
    # alle in dasselbe), sagt dessen Änderungszeit nichts über EINE davon.
    log_zaehler: dict[str, int] = {}
    for e in eintraege:
        if e[5] is not None:
            log_zaehler[str(e[5])] = log_zaehler.get(str(e[5]), 0) + 1
    for plan, befehl, pausiert, pfad, beschreibung, log in eintraege:
        kennung = _kennung(befehl)
        letzter = None
        if log is not None and log_zaehler.get(str(log), 0) == 1:
            try:
                letzter = log.stat().st_mtime
            except OSError:
                letzter = None
        lauf = laeufe.get(kennung) or {}
        if lauf.get("ende") and (letzter is None or lauf["ende"] > letzter):
            letzter = lauf["ende"]
        ergebnis.append({
            "id": kennung,
            "quelle": "cron",
            "name": _name_aus(pfad, befehl),
            "projekt": _projekt_aus(pfad),
            "beschreibung": beschreibung,
            "befehl": befehl,
            "zeitplan": zeitplan_in_worten(plan),
            "naechster": None if pausiert else naechster_lauf(plan),
            "letzter": letzter,
            "pausiert": pausiert,
            "laeuft": kennung in _laufend,
            "log": str(log) if log else None,
        })
    ergebnis.extend(_timer_lesen())
    # Was als Nächstes dran ist, steht oben; Pausiertes ganz unten.
    ergebnis.sort(key=lambda r: (r["pausiert"], r["naechster"] or float("inf")))
    return ergebnis
