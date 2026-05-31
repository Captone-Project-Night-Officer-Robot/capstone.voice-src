import { useTelemetry } from "./hooks/useTelemetry.js";
import StatePill from "./components/StatePill.jsx";
import VideoWall from "./components/VideoWall.jsx";
import MapCanvas from "./components/MapCanvas.jsx";
import Transcript from "./components/Transcript.jsx";
import CallPanel from "./components/CallPanel.jsx";
import PatientCard from "./components/PatientCard.jsx";
import LogFeed from "./components/LogFeed.jsx";

export default function App() {
  const { connected, robots, logs, activeRobot, setActiveRobot, reset } =
    useTelemetry();
  const ids = Object.keys(robots);
  const robot = activeRobot ? robots[activeRobot] : null;
  const pose = robot?.last_pose;

  return (
    <div className="flex min-h-screen flex-col gap-3 p-3">
      {/* Top bar */}
      <header className="flex shrink-0 items-center justify-between rounded-xl border border-white/5 bg-panel/80 px-4 py-2.5">
        <div className="flex items-center gap-3">
          <h1 className="text-sm font-semibold uppercase tracking-[0.14em] text-ink">
            Night Officer
          </h1>
          <span className="text-xs text-muted">Mission Control</span>
        </div>
        <div className="flex items-center gap-4">
          {ids.length > 1 && (
            <select
              value={activeRobot || ""}
              onChange={(e) => setActiveRobot(e.target.value)}
              className="rounded border border-white/10 bg-panel2 px-2 py-1 text-xs"
            >
              {ids.map((id) => (
                <option key={id} value={id}>
                  {id}
                </option>
              ))}
            </select>
          )}
          <StatePill state={pose?.state} />
          <div className="flex items-center gap-1.5 text-xs">
            <span
              className={`h-2 w-2 rounded-full ${
                connected ? "bg-follow" : "bg-fall animate-pulse2"
              }`}
            />
            <span className="text-muted">
              {connected ? "live" : "reconnecting…"}
            </span>
          </div>
          <button
            onClick={reset}
            className="rounded border border-white/10 bg-white/5 px-2.5 py-1 text-xs hover:bg-white/10"
          >
            reset
          </button>
        </div>
      </header>

      {/* Video wall — full width, fixed-height feeds */}
      <div className="shrink-0">
        <VideoWall />
      </div>

      {/* Main grid: map + conversation | side rail. Fixed row height so the
          three columns get real estate and never collapse/overlap. */}
      <div className="grid shrink-0 grid-cols-1 gap-3 lg:h-[440px] lg:grid-cols-[1.1fr_1fr_320px]">
        <div className="h-[300px] lg:h-auto">
          <MapCanvas robot={robot} />
        </div>
        <div className="h-[300px] lg:h-auto">
          <Transcript lines={robot?.transcript} />
        </div>
        <div className="flex flex-col gap-3 overflow-auto">
          <Stats robot={robot} pose={pose} />
          <CallPanel call={robot?.call} />
          <PatientCard patient={robot?.patient} />
        </div>
      </div>

      {/* Logs — full width */}
      <div className="h-52 shrink-0">
        <LogFeed logs={logs} />
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="flex justify-between text-xs">
      <span className="text-muted">{label}</span>
      <span className="font-mono tabular-nums">{value}</span>
    </div>
  );
}

function Stats({ robot, pose }) {
  const m = robot?.metrics || {};
  const deg = pose ? ((pose.theta * 180) / Math.PI).toFixed(0) + "°" : "—";
  return (
    <section className="flex flex-col gap-1.5 rounded-xl border border-white/5 bg-panel/80 p-3">
      <h2 className="mb-1 text-[11px] font-semibold uppercase tracking-[0.12em] text-muted">
        Telemetry
      </h2>
      <Stat
        label="pose"
        value={pose ? `${pose.x.toFixed(2)}, ${pose.y.toFixed(2)} m` : "—"}
      />
      <Stat label="heading" value={deg} />
      <Stat label="main fps" value={m.main_fps ?? "—"} />
      <Stat label="fall cam fps" value={m.fall_fps ?? "—"} />
      <Stat label="infer ms" value={m.fall_infer_ms ?? "—"} />
      <Stat label="people" value={m.people ?? "—"} />
      <Stat label="path pts" value={robot?.path?.length ?? 0} />
      <Stat label="falls" value={robot?.falls?.length ?? 0} />
    </section>
  );
}
