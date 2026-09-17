/// <reference types="vitest" />
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      // Ikki mustaqil ilova: admin panel (/) va Telegram Mini App (/miniapp/).
      // Alohida entry — Mini App bundle'iga admin kodi (axios, router) kirmaydi.
      input: {
        main: fileURLToPath(new URL("./index.html", import.meta.url)),
        miniapp: fileURLToPath(new URL("./miniapp/index.html", import.meta.url)),
      },
    },
  },
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
