# Night Officer — Voice Agent + Map Dashboard

Autonomous emergency welfare robot voice system + live operator map with
unified log feed and Twilio-based emergency SMS dispatch.
**Stack:** FastAPI · LiveKit Agents · ElevenLabs STT/TTS · Groq (Llama 3.3 70B) · Silero VAD · Krisp Noise Cancellation · HTML5 Canvas dashboard · Twilio SMS

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
├── static/
│   └── dashboard.html      # Live robot map (served at /dashboard)
└── src/
    ├── main.py             # FastAPI app (uvicorn entry point)
    ├── worker.py           # LiveKit worker (separate process)
    ├── agent/
    │   ├── night_officer.py   # Agent subclass (on_enter greeting)
    │   └── session.py         # AgentSession factory (VAD, STT, LLM, TTS)
    ├── api/
    │   ├── health.py          # GET /api/v1/health
    │   ├── session.py         # POST /api/v1/session/start
    │   └── telemetry.py       # pose + fall pins + WebSocket fan-out
    ├── client/
    │   └── livekit.py         # LiveKit JWT token generation
    ├── core/
    │   ├── config.py          # Pydantic Settings (reads .env)
    │   ├── errors.py          # Global exception handlers
    │   ├── exceptions.py      # Domain exception hierarchy
    │   └── logging.py         # Structured logger (loguru)
    ├── models/
    │   ├── session.py         # Pydantic request/response models
    │   └── telemetry.py       # PoseUpdate, FallEvent, LogEvent
    ├── services/
    │   └── notifier.py        # Twilio SMS dispatch for emergency contact
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
- API docs:  http://localhost:8000/docs
- Health:    http://localhost:8000/api/v1/health
- Dashboard: http://localhost:8000/dashboard

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

## Real-time web app (Mission Control) — `/app`

The full live view is the React app at **`/app`**: video feeds, map, live
voice transcript, emergency-call status, patient record, telemetry, and the
merged log feed — all on one page, fed by the telemetry WebSocket. Build it
once with `cd frontend && npm install && npm run build`, then open
`http://<laptop-ip>:8001/app`. See `frontend/README.md` for details. The
minimal map below stays at `/dashboard`.

## Map dashboard + live logs

A second feature lives next to the voice agent — a live operator map at
`/dashboard`, served by the same FastAPI process. The Pi streams its
estimated pose (5 Hz) and a pin every time YOLO detects a fall. The
dashboard renders both on an HTML5 Canvas with auto-fitting view,
state-colored polyline, and a sidebar listing every fall.

A unified **Live Logs** panel merges three sources into one feed:
- `api` — this FastAPI process (loguru sink → WebSocket)
- `worker` — the agent worker (loguru sink → HTTP POST → broadcast)
- `<robot_id>` — Pi-side events (voice start/end, fall confirmation, errors)

```
                                            ┌──────────────────┐
   API loguru ───────────► in-proc sink ──► │                  │
                                            │  ring buffer +   │
   Worker loguru ──► HTTP /telemetry/log ─► │  WS broadcast    │ ─► /dashboard
                                            │     (300 max)    │
   Pi telemetry.emit_log() ─► /telemetry/log│                  │
                                            └──────────────────┘
```

The Pi also publishes pose / fall pins via the same channel:

```
Pi (line_follow --telemetry)
   │   POST /api/v1/telemetry/pose    (5 Hz)
   │   POST /api/v1/telemetry/fall    (on YOLO False → True)
   ▼
FastAPI (this service)
   │
   ▼
WebSocket /api/v1/telemetry/ws   ──→   browser tabs at /dashboard
```

No GPS — pose comes from dead-reckoned motor commands on the Pi. See
`capstone-sensors.src/README.md` for the calibration step.

### Endpoints

```text
POST /api/v1/telemetry/pose      pose update from Pi
POST /api/v1/telemetry/fall      fall pin from Pi
POST /api/v1/telemetry/log       log entry from any source (worker / Pi / scripts)
GET  /api/v1/telemetry/snapshot  full path + falls + recent logs per robot
POST /api/v1/telemetry/reset     clear stored state (?robot_id=… optional)
WS   /api/v1/telemetry/ws        broadcasts updates to dashboards
GET  /dashboard                  static HTML page (the map + logs)
```

> Run with `--workers 1` (uvicorn default). State is in-memory and would
> split across workers otherwise. Persistence (SQLite) is on the
> roadmap below.

## Emergency SMS dispatch (Twilio)

The `NightOfficerAgent` exposes a `dispatch_emergency` LLM tool that the
model is instructed (in `src/prompts/prompts.py`, Step 6) to call once it
has gathered the patient's name, situation, pain, medical history,
allergies, temperature, and alcohol consumption. The tool sends a single
formatted SMS to the configured emergency contact, then the agent
proceeds with the standard Step 6 confirmation lines on-air.

Wire it up in `.env`:

```env
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...          # rotate in the Twilio console if exposed
TWILIO_FROM_NUMBER=+1...       # your Twilio phone number
EMERGENCY_PHONE_NUMBER=+82...  # who gets the SMS
```

Leaving any of these blank disables the feature gracefully — the agent
still speaks its Step 6 lines and the full patient record is written to
the worker log (and the dashboard's Live Logs panel) for diagnostic use.

Trial Twilio accounts can only text *verified* numbers — add the
recipient in **Twilio Console → Phone Numbers → Verified Caller IDs**
before the demo.

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
| 2 | ✅ Current | Map dashboard — robot path + fall pins streamed via WebSocket |
| 3 | ✅ Current | Live Logs panel — API + worker + Pi events merged into one feed |
| 4 | ✅ Current | `dispatch_emergency` LLM tool — Twilio SMS to emergency contact at Step 6 |
| 5 | Planned | `log_triage_result()` tool — structured patient record persisted per session |
| 6 | Planned | SQLite/MongoDB incident persistence (path + falls + transcripts survive restart) |
| 7 | Planned | Simulated 119 voice call via Twilio Programmable Voice |
