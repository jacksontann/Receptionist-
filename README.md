# Sandbox Receptionist

A standalone virtual receptionist for Sandbox Space: an [Anam](https://anam.ai) video
avatar that greets visitors, answers questions about the coworking space, and can switch
language and avatar mid-conversation.

This project is fully self-contained. It does not read from, write to, or import anything
belonging to TalentScreen — no shared database, no shared code, no shared config.

## Layout

```
agent/   LiveKit voice agent (Python) — the receptionist's brain, voice and avatar
web/     Laravel 12 + Inertia + React — provisions the room and renders the UI
```

The browser never talks to `agent/` directly. `web/` creates a LiveKit room, mints a
visitor token, and asks LiveKit to dispatch the agent into that room; both sides then meet
inside LiveKit.

## Prerequisites

PHP 8.2+, Composer, Node 18+, Python 3.12, and accounts for LiveKit, OpenAI and Anam.

## Setup

**1. Agent**

```bash
cd agent
python -m venv venv
venv/Scripts/activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
cp .env.local.example .env.local   # then fill it in
```

**2. Web**

```bash
cd web
composer install
npm install
cp .env.example .env           # then fill in the LIVEKIT_* values
php artisan key:generate
npm run build
```

`LIVEKIT_URL` is the `wss://` endpoint handed to the browser; `LIVEKIT_HOST` is the
`https://` endpoint the backend calls. They are different values and both are required.

## Running

Two processes, in separate terminals:

```bash
cd agent && venv/Scripts/activate && python receptionist.py dev
cd web   && php artisan serve
```

Then open <http://127.0.0.1:8000>. For frontend hot-reload, run `npm run dev` instead of
`npm run build`.

`npm run dev` serves assets on port **5173**, not 8001. The `APP_URL: http://127.0.0.1:8001`
line Vite prints on startup is just echoing `APP_URL` from `web/.env` — it is a label, not a
port Vite listens on. Keep `APP_URL` matching whatever port `php artisan serve` uses (8000 by
default), or Laravel will generate links to a port nothing is running on.

There is no login — opening the page starts a session immediately.

## Configuration notes

**Agent identity.** The worker registers as `receptionist-standalone-agent` on health port
8084, and `web/` dispatches that exact name. If you rename one, rename both, or the agent
will silently never join the room (the controller only logs a warning on dispatch failure).

**Anam concurrency.** A Starter plan permits **one** concurrent avatar session per API key.
If you also run TalentScreen's own receptionist against the same `ANAM_RECEPTIONIST_API_KEY`,
only one of them can hold an avatar at a time — the other retries, then fails. Give this
project its own Anam key if you need both live simultaneously.

**Keeping the two sides in sync.** The language and avatar lists exist in both
`agent/receptionist.py` (`SUPPORTED_LANGUAGES`, `SUPPORTED_AVATARS`) and
`web/resources/js/pages/room/receptionist-room.tsx` (`LANGUAGES`, `AVATARS`). Editing one
without the other will offer the visitor an option the agent rejects.

## Features

Video avatar with live captions and a full conversation transcript; mute; language
switching between English, Chinese and Malay (the agent then stays locked to that
language); avatar switching between Carl and Cara, carrying conversation history across
the swap; and a 20-minute session cap.
