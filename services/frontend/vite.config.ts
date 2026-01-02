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
    // reverse-proxy 経由でアクセスしたとき、HMR クライアントが ws://localhost:5173 に
    // 接続しようとして失敗する場合がある。必要なら環境変数で HMR 接続先を上書きする。
    // 例: VITE_HMR_HOST=100.103.236.14 / VITE_HMR_CLIENT_PORT=80
    // ref: https://vite.dev/config/server-options.html#server-hmr
    hmr: process.env.VITE_HMR_HOST
      ? {
          host: process.env.VITE_HMR_HOST,
          clientPort: Number(process.env.VITE_HMR_CLIENT_PORT || "80"),
          protocol: (process.env.VITE_HMR_PROTOCOL as "ws" | "wss") || "ws",
        }
      : undefined,
  },
});
