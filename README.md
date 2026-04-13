# Night Officer — Voice Agent

Autonomous emergency welfare robot voice system.
**Stack:** FastAPI · LiveKit Agents · ElevenLabs STT/TTS · Claude (Anthropic)

---

## Project structure

```
night-officer/
├── Dockerfile.api          # FastAPI HTTP server image
├── Dockerfile.worker       # LiveKit agent worker image
├── docker-compose.yml      # Runs both services together
├── pyproject.toml          # Linting, type-check, test config
├── requirements.txt
├── .env.example            # Copy to .env and fill in keys
└── src/
    ├── main.py             # FastAPI app (uvicorn entry point)
    ├── worker.py           # LiveKit worker (separate process)
    ├── agent/
    │   ├── __init__.py
    │   ├── night_officer.py   # Agent subclass (on_enter greeting)
    │   ├── prompts.py         # Bilingual system prompt
    │   └── session.py         # AgentSession factory
    ├── api/
    │   ├── __init__.py
    │   ├── middleware/
    │   │   ├── __init__.py
    │   │   ├── errors.py      # Global exception handlers
    │   │   └── logging.py     # Request logging middleware
    │   └── routes/
    │       ├── __init__.py
    │       ├── health.py      # GET /api/v1/health
    │       └── session.py     # POST /api/v1/session/start
    ├── client/
    │   ├── __init__.py
    │   └── livekit.py         # Async token generation
    ├── core/
    │   ├── __init__.py
    │   ├── config.py          # Pydantic Settings (reads .env)
    │   ├── exceptions.py      # Domain exception hierarchy
    │   └── logging.py         # Structured JSON logger
    ├── models/
    │   ├── __init__.py
    │   └── session.py         # Pydantic request/response models
    └── utils/
        └── __init__.py        # Pure helpers (phase 2)
```

---

## Quick start

### 1. Configure environment
```bash
cp .env.example .env
# Fill in: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
#          ANTHROPIC_API_KEY, ELEVEN_API_KEY
```

### 2. Run with Docker Compose
```bash
docker compose up --build
```
- API docs: http://localhost:8000/docs
- Health:   http://localhost:8000/api/v1/health

### 3. Local dev (without Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Terminal 1 — FastAPI
uvicorn src.main:app --reload --port 8000

# Terminal 2 — Agent worker (console = local mic/speaker)
python -m src.worker console   
```

---

## How it works

```
Robot FSM (TRIAGE state)
  → POST /api/v1/session/start   (gets LiveKit room token)
  → joins LiveKit room via WebRTC

LiveKit worker
  → spawns NightOfficerAgent in that room
  → greets in Korean + English
  → STT (ElevenLabs Scribe v2) → Claude → TTS (ElevenLabs flash)
  → bilingual welfare conversation until session ends
```

---

## Phase roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Current | Agent speaks — STT + Claude + TTS pipeline |
| 2 | Planned | `dispatch_alert()` and `log_triage_result()` tools |
| 3 | Planned | MongoDB incident persistence |
| 4 | Planned | Twilio 119 simulated SMS alert |
