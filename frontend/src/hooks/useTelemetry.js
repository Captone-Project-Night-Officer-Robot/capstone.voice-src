import { useEffect, useRef, useState } from "react";

// Connects to the FastAPI telemetry WebSocket and reduces the live message
// stream into per-robot state: pose/path, falls, metrics, transcript, patient
// record, emergency-call status, and the merged log feed.
//
// Message types (from src/api/telemetry.py):
//   snapshot | pose | fall | log | transcript | patient | call | reset | ping

const WS_PATH = "/api/v1/telemetry/ws";
const MAX_LOGS = 300;
const MAX_TRANSCRIPT = 120;

function wsUrl() {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${location.host}${WS_PATH}`;
}

const emptyRobot = () => ({
  path: [],
  falls: [],
  last_pose: null,
  metrics: {},
  transcript: [],
  patient: null,
  call: null,
});

export function useTelemetry() {
  const [connected, setConnected] = useState(false);
  const [robots, setRobots] = useState({});
  const [logs, setLogs] = useState([]);
  const [activeRobot, setActiveRobot] = useState(null);
  const wsRef = useRef(null);
  const activeRef = useRef(null);
  activeRef.current = activeRobot;

  useEffect(() => {
    let stop = false;
    let retry;

    const connect = () => {
      if (stop) return;
      const ws = new WebSocket(wsUrl());
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);
      ws.onclose = () => {
        setConnected(false);
        retry = setTimeout(connect, 1500);
      };
      ws.onerror = () => ws.close();
      ws.onmessage = (ev) => {
        let msg;
        try {
          msg = JSON.parse(ev.data);
        } catch {
          return;
        }
        handle(msg);
      };
    };

    const ensureActive = (id) => {
      if (!activeRef.current && id) setActiveRobot(id);
    };

    const handle = (msg) => {
      switch (msg.type) {
        case "ping":
          return;
        case "snapshot": {
          const next = {};
          for (const [id, r] of Object.entries(msg.robots || {})) {
            next[id] = { ...emptyRobot(), ...r };
          }
          setRobots(next);
          setLogs((msg.logs || []).slice(-MAX_LOGS));
          ensureActive(Object.keys(next)[0]);
          return;
        }
        case "reset": {
          if (msg.robot_id) {
            setRobots((p) => {
              const n = { ...p };
              delete n[msg.robot_id];
              return n;
            });
          } else {
            setRobots({});
            setLogs([]);
          }
          return;
        }
        case "log":
          setLogs((p) => [...p, msg].slice(-MAX_LOGS));
          return;
        case "pose": {
          ensureActive(msg.robot_id);
          setRobots((p) => {
            const r = { ...(p[msg.robot_id] || emptyRobot()) };
            r.last_pose = {
              x: msg.x,
              y: msg.y,
              theta: msg.theta,
              state: msg.state,
              ts: msg.ts,
            };
            r.metrics = msg.metrics || r.metrics;
            if (msg.appended) {
              r.path = [...r.path, { x: msg.x, y: msg.y, state: msg.state, ts: msg.ts }];
            }
            return { ...p, [msg.robot_id]: r };
          });
          return;
        }
        case "fall": {
          ensureActive(msg.robot_id);
          setRobots((p) => {
            const r = { ...(p[msg.robot_id] || emptyRobot()) };
            r.falls = [...r.falls, { x: msg.x, y: msg.y, ts: msg.ts, track_id: msg.track_id }];
            return { ...p, [msg.robot_id]: r };
          });
          return;
        }
        case "transcript": {
          ensureActive(msg.robot_id);
          setRobots((p) => {
            const r = { ...(p[msg.robot_id] || emptyRobot()) };
            let t = [...r.transcript];
            // Interim lines (final=false) replace the trailing interim line of
            // the same role; final lines append.
            const last = t[t.length - 1];
            if (!msg.final && last && !last.final && last.role === msg.role) {
              t[t.length - 1] = { ...msg };
            } else if (!msg.final) {
              t.push({ ...msg });
            } else {
              if (last && !last.final && last.role === msg.role) t.pop();
              t.push({ ...msg });
            }
            r.transcript = t.slice(-MAX_TRANSCRIPT);
            return { ...p, [msg.robot_id]: r };
          });
          return;
        }
        case "patient": {
          ensureActive(msg.robot_id);
          setRobots((p) => {
            const r = { ...(p[msg.robot_id] || emptyRobot()) };
            r.patient = msg;
            return { ...p, [msg.robot_id]: r };
          });
          return;
        }
        case "call": {
          ensureActive(msg.robot_id);
          setRobots((p) => {
            const r = { ...(p[msg.robot_id] || emptyRobot()) };
            r.call = msg;
            return { ...p, [msg.robot_id]: r };
          });
          return;
        }
        default:
          return;
      }
    };

    connect();
    return () => {
      stop = true;
      clearTimeout(retry);
      wsRef.current && wsRef.current.close();
    };
  }, []);

  const reset = () => {
    fetch("/api/v1/telemetry/reset", { method: "POST" }).catch(() => {});
  };

  return { connected, robots, logs, activeRobot, setActiveRobot, reset };
}
