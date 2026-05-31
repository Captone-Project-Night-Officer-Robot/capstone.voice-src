import { useEffect, useRef } from "react";
import Panel from "./Panel.jsx";

const STATE_COLORS = {
  follow: "#4caf6f",
  search: "#f0b232",
  obstacle: "#c97a3a",
  verify: "#b16dff",
  fall: "#e2495a",
  voice: "#5aa7ff",
  resuming: "#6a7686",
  init: "#5a6373",
};

// Canvas map: auto-fitting view of the dead-reckoned path (colored by state)
// plus a red pin at every confirmed fall, and the robot's current pose arrow.
export default function MapCanvas({ robot }) {
  const ref = useRef(null);

  useEffect(() => {
    const cv = ref.current;
    if (!cv) return;
    const ctx = cv.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const w = cv.clientWidth;
    const h = cv.clientHeight;
    cv.width = w * dpr;
    cv.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    ctx.clearRect(0, 0, w, h);

    const path = robot?.path || [];
    const falls = robot?.falls || [];
    const pose = robot?.last_pose;
    const pts = [...path];
    if (pose) pts.push(pose);

    // fit
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const p of pts) {
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
    }
    if (!isFinite(minX)) { minX = -1; maxX = 1; minY = -1; maxY = 1; }
    const m = 1.0;
    minX -= m; maxX += m; minY -= m; maxY += m;
    const s = Math.min(w / Math.max(0.5, maxX - minX), h / Math.max(0.5, maxY - minY));
    const ox = (w - s * (maxX + minX)) / 2;
    const oy = (h + s * (maxY + minY)) / 2;
    const X = (x) => ox + s * x;
    const Y = (y) => oy - s * y;

    // grid
    ctx.strokeStyle = "#161b22";
    ctx.lineWidth = 1;
    for (let gx = Math.ceil(minX); gx <= maxX; gx++) {
      ctx.beginPath(); ctx.moveTo(X(gx), 0); ctx.lineTo(X(gx), h); ctx.stroke();
    }
    for (let gy = Math.ceil(minY); gy <= maxY; gy++) {
      ctx.beginPath(); ctx.moveTo(0, Y(gy)); ctx.lineTo(w, Y(gy)); ctx.stroke();
    }

    // path, colored by state segment
    ctx.lineWidth = 3;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    for (let i = 1; i < path.length; i++) {
      ctx.beginPath();
      ctx.strokeStyle = STATE_COLORS[path[i].state] || "#4caf6f";
      ctx.moveTo(X(path[i - 1].x), Y(path[i - 1].y));
      ctx.lineTo(X(path[i].x), Y(path[i].y));
      ctx.stroke();
    }

    // fall pins
    for (const f of falls) {
      ctx.beginPath();
      ctx.arc(X(f.x), Y(f.y), 6, 0, Math.PI * 2);
      ctx.fillStyle = "#e2495a";
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // robot pose
    if (pose) {
      const px = X(pose.x), py = Y(pose.y);
      ctx.save();
      ctx.translate(px, py);
      ctx.rotate(-(pose.theta || 0));
      ctx.beginPath();
      ctx.moveTo(12, 0); ctx.lineTo(-7, 6); ctx.lineTo(-7, -6); ctx.closePath();
      ctx.fillStyle = STATE_COLORS[pose.state] || "#5aa7ff";
      ctx.fill();
      ctx.restore();
    }
  }, [robot]);

  return (
    <Panel title="Map · path + falls" className="h-full">
      <canvas ref={ref} className="h-full w-full rounded-lg" />
    </Panel>
  );
}
