import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served by FastAPI under /app, with built assets written into ../static/app
// so main.py can mount them. During `npm run dev`, /api and the telemetry
// WebSocket are proxied to the FastAPI server on :8001.
export default defineConfig({
  plugins: [react()],
  base: "/app/",
  build: {
    outDir: "../static/app",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8001",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
