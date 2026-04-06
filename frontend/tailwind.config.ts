import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        // Spec-exact design tokens
        surface: "#0F172A",  // page background
        card: "#1E293B",     // card background
        border: "#334155",   // card/input borders
        muted: "#94A3B8",    // secondary text
        // Grade colors (Bella spec)
        "grade-a": "#22C55E",
        "grade-b": "#3B82F6",
        "grade-c": "#F59E0B",
        "grade-d": "#F97316",
        "grade-f": "#EF4444",
        // Phase 2: Channel colors (hue separation ≥60°, WCAG AA on dark bg)
        "channel-web": "#3B82F6",    // Blue 500 — website
        "channel-media": "#F59E0B",  // Amber 500 — media
        "channel-social": "#EC4899", // Pink 500 — social
        "channel-auth": "#A78BFA",   // Violet 400 — authority
      },
      fontFamily: {
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
    },
  },
  plugins: [],
};
export default config;
