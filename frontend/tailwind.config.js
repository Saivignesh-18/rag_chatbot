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
        // Brand palette (sage green) for a calm, light enterprise feel.
        brand: {
          50: "#f4f7f3",
          100: "#e5ece2",
          200: "#cdd9c8",
          300: "#b2c6aa",
          400: "#98b68c",
          500: "#7a9a6e",
          600: "#607b56",
          700: "#4b6144",
          800: "#3d4e38",
          900: "#334130",
          950: "#26301f",
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
        display: [
          "Plus Jakarta Sans",
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "sans-serif",
        ],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(122,154,110,0.25), 0 8px 30px rgba(96,123,86,0.18)",
        card: "0 1px 2px rgba(51,65,48,0.05), 0 8px 24px rgba(51,65,48,0.07)",
        soft: "0 1px 2px rgba(51,65,48,0.04), 0 10px 34px rgba(51,65,48,0.10)",
        glass: "0 8px 32px rgba(51,65,48,0.14), inset 0 1px 0 rgba(255,255,255,0.6)",
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
