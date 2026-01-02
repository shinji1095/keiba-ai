import { defineConfig } from "@playwright/test";

// System tests run against an already running environment (reverse-proxy → frontend/api → Pi scraper).
// Use PW_BASE_URL to point to the PC's reverse-proxy, e.g.:
//   PW_BASE_URL=http://reverse-proxy npm run test:e2e:system
//   PW_BASE_URL=http://100.103.236.14 npm run test:e2e:system
export default defineConfig({
  testDir: "tests/system",
  timeout: 60_000,
  expect: {
    timeout: 10_000,
  },
  use: {
    baseURL: process.env.PW_BASE_URL || "http://reverse-proxy",
    trace: "on-first-retry",
  },
});


