# Night Officer — Voice Agent

Autonomous emergency welfare robot voice system.
**Stack:** FastAPI · LiveKit Agents · ElevenLabs STT/TTS · Groq (Llama 3.3 70B) · Silero VAD · Krisp Noise Cancellation

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
    │   ├── night_officer.py   # Agent subclass (on_enter greeting)
    │   └── session.py         # AgentSession factory (VAD, STT, LLM, TTS)
    ├── api/
    │   ├── health.py          # GET /api/v1/health
    │   └── session.py         # POST /api/v1/session/start
    ├── client/
    │   └── livekit.py         # LiveKit JWT token generation
    ├── core/
    │   ├── config.py          # Pydantic Settings (reads .env)
    │   ├── errors.py          # Global exception handlers
    │   ├── exceptions.py      # Domain exception hierarchy
    │   └── logging.py         # Structured logger (loguru)
    ├── models/
    │   └── session.py         # Pydantic request/response models
    └── prompts/
        └── prompts.py         # System prompt + greeting instruction
```

---

## Quick start

### 1. Configure environment
```bash
cp .env.example .env
# Fill in: LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET,
#          GROQ_API_KEY, ELEVEN_API_KEY, ELEVEN_VOICE_ID
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
  → greets in English
  → Noise cancellation (Krisp BVC) → VAD (Silero) → STT (ElevenLabs Scribe v2)
  → Groq Llama 3.3 70B → TTS (ElevenLabs flash)
  → welfare conversation until session ends
```

---

## Audio pipeline features

| Feature | Implementation |
|---|---|
| Noise & echo cancellation | Krisp BVC via `livekit-plugins-noise-cancellation` |
| Voice activity detection | Silero VAD (tunable thresholds) |
| Turn detection | MultilingualModel (ML-based end-of-utterance) |
| Interruption handling | Enabled — user can interrupt agent mid-speech |

---

## Phase roadmap

| Phase | Status | Description |
|-------|--------|-------------|
| 1 | ✅ Current | Agent speaks — STT + LLM + TTS pipeline |
| 2 | Planned | `dispatch_alert()` and `log_triage_result()` tools |
| 3 | Planned | MongoDB incident persistence |
| 4 | Planned | Twilio 119 simulated SMS alert |
