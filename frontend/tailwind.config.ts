import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        apple: {
          bg: "#F5F5F7",
          card: "#FFFFFF",
          ink: "#1D1D1F",
          muted: "#86868B",
          blue: "#007AFF",
          line: "rgba(0,0,0,0.08)",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "SF Pro Display",
          "SF Pro Text",
          "Helvetica Neue",
          "sans-serif",
        ],
        mono: ["SF Mono", "ui-monospace", "Menlo", "monospace"],
      },
      borderRadius: {
        apple: "12px",
      },
      boxShadow: {
        window: "0 22px 70px rgba(0,0,0,0.18), 0 2px 8px rgba(0,0,0,0.06)",
        card: "0 1px 2px rgba(0,0,0,0.04), 0 8px 24px rgba(0,0,0,0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
