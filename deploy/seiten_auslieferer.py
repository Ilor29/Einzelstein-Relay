#!/usr/bin/env python3
"""Auslieferer für den Webspace (Dienst seiten-roli, Lea und Lorenz gleich gebaut).

Verhält sich wie `python3 -m http.server`, mit einer Ausnahme: Wird eine
HTML-Seite mit `?kommentieren=1` aufgerufen, hängt er vor </body> ein kleines
Hilfsskript an. Das Skript markiert beim Überfahren ein Element und meldet beim
Anklicken per postMessage an die umgebende Seite (die Relay-App), was gewählt
wurde. Ohne den Parameter bleibt jede Seite Byte für Byte unverändert.
(Baustein 11, Roli 04.11.2026 „3. Ja“.)

Aufruf: seiten_auslieferer.py PORT VERZEICHNIS
"""
import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs

HILFSSKRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kommentier-hilfe.js")


def _hilfe() -> bytes:
    with open(HILFSSKRIPT, "rb") as f:
        return b"<script>" + f.read() + b"</script>"


class Handler(SimpleHTTPRequestHandler):
    def _kommentieren(self) -> bool:
        q = parse_qs(urlsplit(self.path).query)
        return q.get("kommentieren") == ["1"]

    def send_head(self):
        if not self._kommentieren():
            return super().send_head()
        pfad = self.translate_path(self.path)
        if os.path.isdir(pfad):
            pfad = os.path.join(pfad, "index.html")
        if not pfad.lower().endswith((".html", ".htm")) or not os.path.isfile(pfad):
            return super().send_head()
        import io
        with open(pfad, "rb") as f:
            roh = f.read()
        marke = roh.lower().rfind(b"</body>")
        hilfe = _hilfe()
        daten = roh[:marke] + hilfe + roh[marke:] if marke >= 0 else roh + hilfe
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(daten)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        return io.BytesIO(daten)


if __name__ == "__main__":
    port, verzeichnis = int(sys.argv[1]), sys.argv[2]
    server = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=verzeichnis))
    server.serve_forever()
