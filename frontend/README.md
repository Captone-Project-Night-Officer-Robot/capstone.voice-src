# Night Officer — Mission Control (real-time web app)

React + Vite + Tailwind single-page app that shows the whole system live on
one page:

- **Live video** — the Pi's three MJPEG feeds (line-follow, white-line mask,
  YOLO fall detection) embedded straight from the Pi (`<pi-ip>:8080`).
- **Map** — dead-reckoned path colored by state + a pin at every fall.
- **Voice conversation** — the patient ↔ Night Officer transcript, streaming
  live (STT + TTS), plus the emergency-call dispatch ↔ contact transcript.
- **Emergency call** — 119 call status (placing → ringing → on call → ended).
- **Patient record** — the info the agent collected at dispatch.
- **Telemetry + live logs** — fps, pose, and the merged api/worker/Pi log feed.

It is served by the FastAPI app at **`/app`** and feeds off the existing
telemetry WebSocket (`/api/v1/telemetry/ws`) — no separate server.

## Build (once, and after any frontend change)

```bash
cd frontend
npm install
npm run build      # outputs to ../static/app, served by FastAPI at /app
```

Then start the API as usual and open it:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
# → http://<laptop-ip>:8001/app
```

The old minimal map stays at `/dashboard`.

## Live-reload dev (optional)

```bash
npm run dev        # http://localhost:5173/app/  (proxies /api + ws to :8001)
```

Run the FastAPI server on :8001 alongside it.

## Setup at demo time

1. Open `http://<laptop-ip>:8001/app` on a browser that's on the **same
   Wi-Fi as the Pi** (required for the video feeds).
2. In the **Live video** panel, type the **Pi's IP** (e.g. `172.20.10.5`)
   and hit *set* — saved in the browser, the three feeds appear.
   (Run the Pi with `--stream` so port 8080 is serving.)
