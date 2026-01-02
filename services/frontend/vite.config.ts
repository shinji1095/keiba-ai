import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
    exclude: ["tests/e2e/**"],
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // reverse-proxy 経由で Host ヘッダが "reverse-proxy" / PC IP になることがあるため許可する
    // （Playwright system テストで reverse-proxy を叩くケース）
    allowedHosts: ["reverse-proxy", "100.103.236.14", "localhost", "127.0.0.1"],
  },
});
