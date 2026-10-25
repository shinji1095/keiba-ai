import { defineConfig } from "@playwright/test";

// System tests run against an already running environment (web → frontend/api → PC-local scraper).
// Use PW_BASE_URL to point to the PC's web, e.g.:
//   PW_BASE_URL=http://web npm run test:e2e:system
//   PW_BASE_URL=http://localhost npm run test:e2e:system
export default defineConfig({
  testDir: "tests/system",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: process.env.PW_BASE_URL || "http://web",
    trace: "on-first-retry",
  },
});


