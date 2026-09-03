import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// The backend does not enable CORS, so the dev server proxies `/api` to it and
// strips the prefix. Production builds point `VITE_API_BASE_URL` at the API.
const apiTarget = process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // Pin every build-time setting so a developer's local .env cannot change the
    // result. The empty values are also the shape an unfilled .env line takes.
    env: {
      VITE_SUPABASE_URL: "",
      VITE_SUPABASE_ANON_KEY: "",
      VITE_API_BASE_URL: "",
      VITE_CONSENT_POLICY_VERSION: "",
    },
  },
});
