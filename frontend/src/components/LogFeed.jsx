import { useEffect, useRef, useState } from "react";
import Panel from "./Panel.jsx";

const LEVEL_COLOR = {
  DEBUG: "text-resuming",
  INFO: "text-follow",
  WARNING: "text-search",
  ERROR: "text-fall",
  CRITICAL: "text-fall",
};
const ORDER = { DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3, CRITICAL: 3 };

export default function LogFeed({ logs }) {
  const [min, setMin] = useState("INFO");
  const bodyRef = useRef(null);
  const filtered = (logs || []).filter(
    (l) => ORDER[(l.level || "INFO").toUpperCase()] >= ORDER[min]
  );
  useEffect(() => {
    // Scroll only this panel's body to the bottom — never the page.
    const el = bodyRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    if (atBottom) el.scrollTop = el.scrollHeight;
  }, [filtered.length]);

  const fmt = (ts) =>
    new Date((ts || 0) * 1000).toLocaleTimeString("en-GB", { hour12: false });

  return (
    <Panel
      title="Live logs"
      bodyRef={bodyRef}
      className="h-full"
      right={
        <select
          value={min}
          onChange={(e) => setMin(e.target.value)}
          className="rounded border border-white/10 bg-panel2 px-1.5 py-0.5 text-xs text-ink outline-none"
        >
          <option value="DEBUG">all</option>
          <option value="INFO">info+</option>
          <option value="WARNING">warn+</option>
          <option value="ERROR">errors</option>
        </select>
      }
    >
      <div className="font-mono text-[11px] leading-relaxed">
        {filtered.length === 0 && (
          <div className="italic text-muted">No logs yet.</div>
        )}
        {filtered.map((l, i) => (
          <div key={i} className="grid grid-cols-[58px_52px_56px_1fr] gap-2">
            <span className="text-muted">{fmt(l.ts)}</span>
            <span className={`font-bold ${LEVEL_COLOR[(l.level || "").toUpperCase()] || ""}`}>
              {(l.level || "").toUpperCase()}
            </span>
            <span className="text-muted">{l.source}</span>
            <span className="whitespace-pre-wrap break-words">{l.message}</span>
          </div>
        ))}
      </div>
    </Panel>
  );
}
