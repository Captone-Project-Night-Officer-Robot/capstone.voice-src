import Panel from "./Panel.jsx";

// Emergency 119 call status: placing → ringing → active → ended (or failed).
const STATUS = {
  placing: { label: "Placing call", color: "text-search", dot: "bg-search animate-pulse2" },
  ringing: { label: "Ringing", color: "text-voice", dot: "bg-voice animate-pulse2" },
  active: { label: "On call", color: "text-follow", dot: "bg-follow animate-pulse2" },
  ended: { label: "Call ended", color: "text-muted", dot: "bg-muted" },
  failed: { label: "Call failed", color: "text-fall", dot: "bg-fall" },
};

export default function CallPanel({ call }) {
  const st = call ? STATUS[call.status] || STATUS.ended : null;
  return (
    <Panel title="Emergency call · 119">
      {!call ? (
        <div className="text-xs italic text-muted">No call yet.</div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${st.dot}`} />
            <span className={`text-sm font-semibold ${st.color}`}>{st.label}</span>
          </div>
          {call.to && (
            <div className="flex justify-between text-xs">
              <span className="text-muted">to</span>
              <span className="font-mono">{call.to}</span>
            </div>
          )}
          {call.detail && (
            <div className="flex justify-between text-xs">
              <span className="text-muted">detail</span>
              <span>{call.detail}</span>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
