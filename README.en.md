# Einzelstein Relay

Diese Seite auf Deutsch: [README.md](README.md)

Your own AI workspace on your own server — driven from your phone, by
voice. You dictate, the answer is read out loud to you. Conversations run
as Claude Code sessions inside tmux on your server: they keep working
while your phone sits in your pocket, and at your desk you pick up exactly
where you left off on the road.

Einzelstein Relay is an independent project by Einzelstein Software. It
works together with Claude Code (Anthropic) but is not an Anthropic
product; you sign in with your own Claude account.

## What you get

- All conversations as cards in one overview: pin them, put them to
  sleep, archive them. You see at a glance what is running and what is
  waiting for you.
- Tap the microphone and talk; answers are read out by a local voice
  (Piper). If you prefer, add your own API keys for cloud voices.
- A built-in "Brain": an overview chat that knows your projects and
  explains how things work.
- A guided tour that shows first-time users around.
- Bundled skills, such as CODE//GUARD for code and legal review. They
  update themselves along with the app.
- The app notifies you when a session finishes or has a question for you
  (web push).

A word of honesty: the app, its voices, the guided tour and the
step-by-step guide are currently **German only**. Everything works in an
English-speaking setup too — Claude answers in whatever language you use —
but the buttons and explanations around it speak German for now. If enough
people ask, an English interface is on the table.

## What you need

- A small Linux server (Debian or Ubuntu, 4 GB RAM or more, roughly
  5–10 € per month at providers like Hetzner or Hostinger). No domain
  required; the address is derived from the server's IP (sslip.io).
- Your own Claude subscription (Anthropic) to sign in Claude Code.
- A phone with Chrome, ideally Android. On iPhone, reading aloud works in
  Chrome; dictation is limited there by Apple's platform rules.

## Getting it onto your server

The convenient way: when creating the server, paste the contents of
[`deploy/cloud-init.yaml`](deploy/cloud-init.yaml) into the "cloud config"
field. The server sets itself up on first boot; then open the server's
address on your phone and tap the connect button — the first device needs
no code (for 24 hours, as long as no device is registered yet). Finally,
use Chrome's menu and "Add to Home screen".

The manual way:

```bash
git clone https://github.com/Ilor29/Einzelstein-Relay.git ~/Hetzner-App
cd ~/Hetzner-App
./scripts/setup.sh
```

The script installs everything (packages, Python environment, Claude Code,
Piper with a voice, Caddy with HTTPS, the service) and prints the address
plus a pairing code at the end. It is safe to run more than once. A
detailed German walk-through for non-technical users lives in
[`ANLEITUNG.md`](ANLEITUNG.md).

Additional devices join via a pairing code: a connected device generates
it in the settings, the new device types it in.

## Security

This app gives access to your server, and it treats that door
accordingly:

- No passwords — device keys. Each phone generates its own key pair, and
  the private half never leaves the device. Sign-in works by signature;
  there is nothing to intercept and nothing to guess.
- Only registered devices get in. You revoke a lost phone in the
  settings, immediately and including its running session.
- The service listens on 127.0.0.1 only; the outside world talks
  exclusively to Caddy, over HTTPS.
- The first-visitor pairing (first device without a code) is deliberately
  double-limited and was reviewed beforehand — the trade-off and residual
  risk are documented openly in
  [`CODE-GUARD-Bericht-Erstkopplung.md`](CODE-GUARD-Bericht-Erstkopplung.md)
  (German).

## Where your data lives

Files, projects and transcripts stay on your server; reading aloud runs
there via Piper, no cloud involved. Whenever Claude works, the content of
the conversation goes to Anthropic, because that is where the model runs —
exactly as in the official Claude app, through your own account. Only if
you enable them yourself: browser dictation (Google) and cloud voices
(your own key). The maker of this app sees none of it: no phone-home, no
telemetry, no license server.

## Developing

No build step: edit a file, reload the page.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
./scripts/install-piper.sh
.venv/bin/python -m hetzner_app.server
# → http://127.0.0.1:8787
```

The parts: `hetzner_app/tmux.py` (sessions), `state.py` (state), `tts.py`
(reading aloud), `geraete.py` (devices and pairing), `server.py` (the
API), `web/` (the PWA).

## Licensing

Third-party components and their licenses are listed in
[`THIRD-PARTY-LICENSES.md`](THIRD-PARTY-LICENSES.md). The Piper voice
engine deliberately runs as a separate process.

This project is public but not yet under an open license — all rights
reserved. Looking around, trying it out and running it on your own server
is explicitly welcome; an open license will follow. Suggestions are
welcome as issues or pull requests — changes are merged exclusively by
the maintainer, because this repository is the update source for running
installations.
