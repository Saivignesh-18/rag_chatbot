/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Semantic tokens backed by CSS variables in index.css.
        // Light is the default (:root); the .dark class swaps the palette.
        // Using rgb(var(--x) / <alpha-value>) keeps Tailwind alpha modifiers
        // (e.g. bg-card/60, text-content/80) working across both themes.
        bg: "rgb(var(--bg) / <alpha-value>)",
        panel: "rgb(var(--panel) / <alpha-value>)",
        card: "rgb(var(--card) / <alpha-value>)",
        card2: "rgb(var(--card2) / <alpha-value>)",
        line: "rgb(var(--line) / <alpha-value>)",
        content: "rgb(var(--content) / <alpha-value>)",
        muted: "rgb(var(--muted) / <alpha-value>)",
        subtle: "rgb(var(--subtle) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
        // Brand palette (indigo/violet) for a premium SaaS feel.
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        surface: {
          DEFAULT: "#0b0f1a",
          50: "#f8fafc",
          100: "#f1f5f9",
          800: "#111827",
          900: "#0b0f1a",
          950: "#070a12",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(99,102,241,0.2), 0 8px 30px rgba(79,70,229,0.15)",
        card: "0 1px 2px rgba(0,0,0,0.06), 0 8px 24px rgba(15,23,42,0.06)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "bounce-dot": {
          "0%, 80%, 100%": { transform: "scale(0.6)", opacity: "0.4" },
          "40%": { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: {
        "fade-in": "fade-in 0.3s ease-out both",
        shimmer: "shimmer 1.6s infinite",
      },
    },
  },
  plugins: [],
};
