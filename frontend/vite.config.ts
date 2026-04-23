/// <reference types="vitest" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Faqat haqiqiy API prefiksi — "/api" keng pattern frontend route'lari bilan
      // to'qnashadi (masalan "/api-keys" SPA sahifasi). API_BASE = "/api/v1" (api.ts).
      "/api/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
  },
});
