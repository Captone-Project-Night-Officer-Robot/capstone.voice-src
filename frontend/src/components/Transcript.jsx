import { useEffect, useRef } from "react";
import Panel from "./Panel.jsx";

// agent/dispatch = robot side (blue, left). patient/contact = human (green, right).
const ROBOT_ROLES = new Set(["agent", "dispatch"]);
const LABEL = {
  agent: "Night Officer",
  patient: "Patient",
  dispatch: "Dispatch",
  contact: "Contact",
};

export default function Transcript({ lines }) {
  const bodyRef = useRef(null);
  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100;
    if (atBottom) el.scrollTop = el.scrollHeight;
  }, [lines]);

  return (
    <Panel title="Voice conversation" className="h-full" bodyRef={bodyRef}>
      {(!lines || lines.length === 0) && (
        <div className="text-xs italic text-muted">No conversation yet.</div>
      )}
      <div className="flex flex-col gap-2">
        {(lines || []).map((l, i) => {
          const robot = ROBOT_ROLES.has(l.role);
          return (
            <div
              key={i}
              className={`flex flex-col ${robot ? "items-start" : "items-end"}`}
            >
              <div className="mb-0.5 text-[10px] uppercase tracking-wide text-muted">
                {LABEL[l.role] || l.role}
              </div>
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-1.5 text-sm ${
                  robot
                    ? "rounded-tl-sm bg-voice/15 text-ink"
                    : "rounded-tr-sm bg-follow/15 text-ink"
                } ${l.final ? "" : "opacity-60 italic"}`}
              >
                {l.text}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}
