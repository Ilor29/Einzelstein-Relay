"""Die Skill-Bibliothek.

Claude Code bringt viele Skills mit — jeder als SKILL.md mit einem englischen
Namen und einer englischen Beschreibung, die man nicht ändern kann. Genau das
stört: Man findet sie nicht wieder, weil man sich die Kürzel nicht merkt.

Hier legen wir ein eigenes Etikett darüber: ein deutscher Name, eine eigene
Beschreibung, eine Kategorie. Die Originale bleiben unberührt — wir merken uns
nur die Überlagerung, so wie eine Sitzung ihren Anzeigenamen bekommt, ohne den
technischen zu verlieren.
"""

from __future__ import annotations

import json
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:      # pragma: no cover — im Betrieb ist yaml da
    yaml = None

CLAUDE = Path.home() / ".claude"

# Wo Skills liegen. Nicht das ganze ~/.claude durchsuchen — dort liegen auch die
# Gesprächsmitschriften, und die will man nicht bei jedem Aufruf durchwaten.
WURZELN = [CLAUDE / "skills", CLAUDE / "plugins"]

# Deine Etiketten. Neben den Fotos, im selben App-Ordner.
ETIKETTEN = Path.home() / ".hetzner-app" / "bibliothek.json"


# --- Die Überlagerung: dein deutsches Etikett -------------------------------

def _etiketten_lesen() -> dict:
    try:
        daten = json.loads(ETIKETTEN.read_text(encoding="utf-8"))
        return daten if isinstance(daten, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _etiketten_schreiben(etiketten: dict) -> None:
    ETIKETTEN.parent.mkdir(parents=True, exist_ok=True)
    ETIKETTEN.write_text(
        json.dumps(etiketten, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# --- Das Original: was in der SKILL.md steht --------------------------------

def _kopf_lesen(datei: Path) -> dict:
    """Den Frontmatter-Block (zwischen den beiden ---) einer SKILL.md lesen."""
    try:
        text = datei.read_text(encoding="utf-8")
    except OSError:
        return {}

    if not text.startswith("---"):
        return {}

    ende = text.find("\n---", 3)
    if ende == -1:
        return {}

    block = text[3:ende]

    if yaml is not None:
        try:
            daten = yaml.safe_load(block)
            if isinstance(daten, dict):
                return daten
        except yaml.YAMLError:
            pass

    # Notnagel, falls yaml fehlt oder stolpert: Zeile für Zeile key: value.
    daten: dict = {}
    for zeile in block.splitlines():
        schluessel, trenner, wert = zeile.partition(":")
        if trenner:
            daten[schluessel.strip()] = wert.strip()
    return daten


def _herkunft(ordner: Path) -> str:
    """Aus welchem Plugin ein Skill stammt — als kurzes Schild auf der Karte.

    Die Pfade sind tief verschachtelt, etwa
    .../plugins/marketplaces/…/plugins/plugin-dev/skills/hook-development.
    Uns interessiert der Plugin-Name direkt vor dem skills-Ordner, also die
    *letzte* Stufe „plugins" bzw. „external_plugins".
    """
    teile = ordner.parts
    for i in range(len(teile) - 1, 0, -1):
        if teile[i] in ("plugins", "external_plugins") and i + 1 < len(teile):
            kandidat = teile[i + 1]
            if kandidat != "marketplaces":
                return kandidat
    # Direkt unter ~/.claude/skills? Dann ist es ein selbstgebauter Skill.
    if ordner.parent == CLAUDE / "skills":
        return "eigen"
    return "Claude Code"


# --- Die Zusammenschau ------------------------------------------------------

def liste() -> list[dict]:
    """Alle Skills — Original und dein Etikett in einem."""
    etiketten = _etiketten_lesen()
    skills: list[dict] = []
    gesehen: set[str] = set()

    for wurzel in WURZELN:
        if not wurzel.is_dir():
            continue
        for datei in wurzel.rglob("SKILL.md"):
            ordner = datei.parent
            kennung = str(ordner.relative_to(CLAUDE))
            if kennung in gesehen:
                continue
            gesehen.add(kennung)

            kopf = _kopf_lesen(datei)
            name = str(kopf.get("name") or ordner.name)
            beschreibung = str(kopf.get("description") or "").strip()
            etikett = etiketten.get(kennung, {})

            skills.append({
                "id": kennung,
                "original_name": name,
                "original_beschreibung": beschreibung,
                "herkunft": _herkunft(ordner),
                # Der Befehl, den man in die Sitzung tippt, um den Skill zu rufen.
                "befehl": "/" + name,
                # Dein Etikett — leer, solange du keins vergeben hast.
                "name": etikett.get("name", ""),
                "beschreibung": etikett.get("beschreibung", ""),
                "kategorie": etikett.get("kategorie", ""),
            })

    # Nach dem sichtbaren Namen sortieren — deiner, sonst der originale.
    skills.sort(key=lambda s: (s["name"] or s["original_name"]).lower())
    return skills


def setzen(kennung: str, name: str, beschreibung: str, kategorie: str) -> None:
    """Dein Etikett für einen Skill setzen — oder wieder abnehmen."""
    etiketten = _etiketten_lesen()

    eintrag = {
        "name": name.strip()[:80],
        "beschreibung": beschreibung.strip()[:500],
        "kategorie": kategorie.strip()[:40],
    }

    # Ist alles leer, entfernen wir die Überlagerung ganz — dann steht wieder
    # das Original da, statt einer leeren Hülle im Etiketten-Speicher.
    if not any(eintrag.values()):
        etiketten.pop(kennung, None)
    else:
        etiketten[kennung] = eintrag

    _etiketten_schreiben(etiketten)
