"""Arbeiter fürs eigene Diktat: läuft mit dem Python aus ~/werkzeuge/whisper/.venv
(dort liegt faster-whisper), nicht im Dienst selbst. Liest Zeilen mit JSON
{"wav": Pfad, "hinweis": Text} von stdin und antwortet je mit einer JSON-Zeile
{"text": ...}. Das Modell wird beim ersten Auftrag geladen und bleibt warm;
nach zehn Minuten ohne Auftrag beendet sich der Arbeiter von selbst, der
Dienst startet ihn beim nächsten Diktat neu."""
import json
import select
import sys

LEERLAUF = 600
modell = None

while True:
    bereit, _, _ = select.select([sys.stdin], [], [], LEERLAUF)
    if not bereit:
        break
    zeile = sys.stdin.readline()
    if not zeile:
        break
    try:
        auftrag = json.loads(zeile)
        if modell is None:
            from faster_whisper import WhisperModel
            modell = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=8)
        segmente, _ = modell.transcribe(
            auftrag["wav"], language="de", beam_size=5,
            vad_filter=True, condition_on_previous_text=False,
            initial_prompt=auftrag.get("hinweis") or None,
        )
        text = " ".join(s.text.strip() for s in segmente).strip()
        antwort = {"text": text}
    except Exception as fehler:      # der Dienst meldet es weiter
        antwort = {"fehler": f"{type(fehler).__name__}: {fehler}"}
    sys.stdout.write(json.dumps(antwort, ensure_ascii=False) + "\n")
    sys.stdout.flush()
