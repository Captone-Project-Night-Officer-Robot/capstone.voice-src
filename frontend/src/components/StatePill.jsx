const COLORS = {
  follow: "bg-follow/20 text-follow",
  search: "bg-search/20 text-search",
  obstacle: "bg-obstacle/20 text-obstacle",
  verify: "bg-verify/20 text-verify",
  fall: "bg-fall/20 text-fall",
  voice: "bg-voice/20 text-voice",
  resuming: "bg-resuming/20 text-resuming",
  init: "bg-white/10 text-muted",
};

export default function StatePill({ state }) {
  const s = (state || "init").toLowerCase();
  const cls = COLORS[s] || COLORS.init;
  return (
    <span
      className={`inline-block rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${cls}`}
    >
      {s}
    </span>
  );
}
