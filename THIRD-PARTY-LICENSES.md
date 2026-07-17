# Fremd-Lizenzen (Third-Party Licenses)

Diese App nutzt fremde Bausteine. Hier steht, welche — mit ihrer Lizenz. Pflicht,
sobald die App verkauft oder weitergegeben wird.

> **Entwurf, Stand 18.07.2026.** Die Lizenzen stammen aus den Paket-Metadaten der
> installierten Fassungen. Vor einem echten Verkauf einmal mit einem
> Lizenz-Scanner (`pip-licenses`) gegenprüfen und die mit „zu bestätigen"
> markierten Zeilen absichern.

---

## ⚠ Der eine Punkt, der eine Entscheidung braucht: Piper (Sprachausgabe)

**piper-tts 1.4.2 — GPL-3.0-or-later.**

Das ist die einzige nicht-freizügige Lizenz im ganzen Paket, und sie sitzt an
einer heiklen Stelle: `hetzner_app/tts.py` importiert Piper **direkt in den
eigenen Prozess** (`from piper import PiperVoice`). Die GPL verlangt bei so einer
engen Verbindung, dass das Gesamtwerk unter GPL steht und der Quellcode
offengelegt wird. Für eine App, die verkauft werden soll, ist das ein echter
Stolperstein — kein Randthema.

Drei Wege (Entscheidung steht aus, gehört zum Fachanwalt):
1. **Abkoppeln:** Piper nur noch als eigenen Prozess/Kommandozeile aufrufen statt
   im selben Prozess zu importieren — dann ist die Verbindung lockerer und die
   GPL greift nur auf Piper selbst, nicht auf die App.
2. **Ersetzen:** eine Sprachausgabe mit freizügiger Lizenz suchen.
3. **Akzeptieren:** die App selbst unter GPL stellen und den Quellcode offenlegen
   (passt in der Regel nicht zum Verkaufsmodell).

Der frühere CODE//GUARD-Bericht hatte Piper fälschlich als MIT geführt — das ist
hiermit richtiggestellt.

---

## Die Stimmen (Sprachmodelle)

Getrennt von der Piper-Software zu betrachten — die Modelle haben eigene Lizenzen
(siehe die Kommentare in `hetzner_app/tts.py`):

- **Thorsten** („Jonas", „Jonas · fein", „Max") und **Kerstin** („Marie") — als
  Stimmen mit klarer, verkaufbarer Lizenz ausgewählt.
- **MLS (medium)** — steht unter **CC-BY 4.0**: verkaufbar, aber **nur mit
  Namensnennung**. Wird die MLS-Stimme mitgeliefert, muss im Impressum/Abspann
  ein Credit stehen: „Stimmen: MLS, CC-BY 4.0". Sonst die MLS-Stimme entfernen.

---

## Oberfläche (Frontend)

- **xterm.js** (+ `xterm-addon-fit`) — **MIT-Lizenz**. © The xterm.js authors,
  SourceLair, Christopher Jeffrey. Volltext: `web/vendor/xterm.LICENSE.txt`.

---

## Server (Python-Pakete)

Alle folgenden Pakete sind **freizügig lizenziert** (MIT, BSD, Apache-2.0,
MPL-2.0, PSF) — verkaufbar, in der Regel nur mit Beibehaltung des Lizenz-Hinweises.

**MIT:** annotated-types, charset-normalizer, h11, http_ece, onnxruntime,
pathvalidate, PyYAML, watchfiles, uvloop (MIT/Apache).

**Apache-2.0:** aiohttp (Apache/MIT), aiosignal, flatbuffers, frozenlist,
multidict, propcache, python-multipart, requests, yarl.

**BSD:** esprima, protobuf (3-Clause BSD), python-dotenv (BSD-3-Clause).

**MPL-2.0:** certifi, py-vapid, pywebpush.

**PSF (Python Software Foundation):** aiohappyeyeballs.

**Lizenz nicht in den Metadaten hinterlegt — zu bestätigen** (durchweg bekannte,
freizügige Projekte; Klammer = allgemein bekannte Lizenz): anyio (MIT),
attrs (MIT), cffi (MIT), click (BSD), cryptography (Apache-2.0/BSD),
fastapi (MIT), httptools (MIT), idna (BSD), numpy (BSD), packaging (Apache/BSD),
pip (MIT), pycparser (BSD), pydantic (MIT), pydantic-core (MIT), starlette (BSD),
typing-inspection (MIT), typing-extensions (PSF), urllib3 (MIT), uvicorn (BSD),
websockets (BSD).

---

## Neu erzeugen (vor Verkauf)

```bash
.venv/bin/pip install pip-licenses
.venv/bin/pip-licenses --format=markdown --with-urls --with-license-file
```

Damit bekommt man eine vollständige, belastbare Liste inklusive Volltext jeder
Lizenz — die kann diese Übersicht dann ersetzen.
