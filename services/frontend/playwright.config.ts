import { defineConfig } from "@playwright/test";

const port = Number(process.env.PW_PORT || "5174");
const baseURL = process.env.PW_BASE_URL || `http://127.0.0.1:${port}`;

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 30_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL,
    trace: "on-first-retry",
  },
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${port}`,
    url: baseURL,
    reuseExistingServer: false,
  },
});
