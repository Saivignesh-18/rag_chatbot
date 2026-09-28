import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Frontend dev server runs on port 3000 (matches default CORS_ORIGINS).
// API calls to /api are proxied to the FastAPI backend during development.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 3000,
    host: true,
    proxy: {
      "/api": {
        target: process.env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    port: 3000,
    host: true,
  },
  build: {
    rollupOptions: {
      output: {
        // Split large vendors so the initial bundle stays lean and cacheable.
        manualChunks: {
          "react-vendor": ["react", "react-dom", "react-router-dom"],
          charts: ["recharts"],
          motion: ["framer-motion"],
          markdown: ["react-markdown", "remark-gfm"],
        },
      },
    },
    chunkSizeWarningLimit: 700,
  },
});
