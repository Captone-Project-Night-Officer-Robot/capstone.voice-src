/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#e8eef5",
        muted: "#8a96a6",
        panel: "#161a21",
        panel2: "#0f1318",
        bg: "#0b0d11",
        follow: "#4caf6f",
        search: "#f0b232",
        obstacle: "#c97a3a",
        verify: "#b16dff",
        fall: "#e2495a",
        voice: "#5aa7ff",
        resuming: "#6a7686",
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      keyframes: {
        pulse2: {
          "0%,100%": { opacity: "1" },
          "50%": { opacity: "0.35" },
        },
      },
      animation: {
        pulse2: "pulse2 1.1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
