import { useEffect, useState } from "react";
import Panel from "./Panel.jsx";

// The Pi serves three MJPEG streams on port 8080:
//   /stream.mjpg (annotated) · /mask.mjpg (white-line) · /fall.mjpg (YOLO)
// We embed them straight from the Pi. The Pi IP is entered once and saved
// in localStorage (the browser must be on the same network as the Pi).

const FEEDS = [
  { key: "stream.mjpg", label: "Pi camera · line follow" },
  { key: "mask.mjpg", label: "White-line mask" },
  { key: "fall.mjpg", label: "Fall detection · YOLO" },
];

function Feed({ label, url }) {
  const [err, setErr] = useState(false);
  useEffect(() => setErr(false), [url]);
  return (
    <div className="relative overflow-hidden rounded-lg border border-white/10 bg-black">
      <div className="absolute left-2 top-2 z-10 rounded bg-black/60 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted">
        {label}
      </div>
      {url && !err ? (
        <img
          src={url}
          alt={label}
          onError={() => setErr(true)}
          className="h-56 w-full bg-black object-contain md:h-64 lg:h-72"
        />
      ) : (
        <div className="flex h-56 w-full items-center justify-center text-center text-xs text-muted md:h-64 lg:h-72">
          {url ? "no signal" : "set Pi IP →"}
        </div>
      )}
    </div>
  );
}

export default function VideoWall() {
  const [piIp, setPiIp] = useState(() => localStorage.getItem("piIp") || "");
  const [draft, setDraft] = useState(piIp);

  const save = () => {
    const v = draft.trim();
    setPiIp(v);
    localStorage.setItem("piIp", v);
  };

  const base = piIp ? `http://${piIp}:8080` : "";

  return (
    <Panel
      title="Live video"
      right={
        <div className="flex items-center gap-1">
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && save()}
            placeholder="Pi IP e.g. 172.20.10.5"
            className="w-40 rounded border border-white/10 bg-panel2 px-2 py-1 text-xs text-ink outline-none focus:border-voice"
          />
          <button
            onClick={save}
            className="rounded border border-white/10 bg-white/5 px-2 py-1 text-xs hover:bg-white/10"
          >
            set
          </button>
        </div>
      }
    >
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        {FEEDS.map((f) => (
          <Feed
            key={f.key}
            label={f.label}
            url={base ? `${base}/${f.key}` : ""}
          />
        ))}
      </div>
    </Panel>
  );
}
