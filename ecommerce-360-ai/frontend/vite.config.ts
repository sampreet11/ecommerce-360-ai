import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In dev, /api is proxied to the FastAPI backend (no CORS issues). In Docker, nginx does the same.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": { target: process.env.VITE_BACKEND_URL ?? "http://127.0.0.1:8000", changeOrigin: true } } },
});
