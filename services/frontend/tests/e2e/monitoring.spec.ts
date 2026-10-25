import { expect, test, type Page } from "@playwright/test";

async function monitorFixture(page: Page, empty = false) {
  const now = new Date(),
    at = now.toISOString();
  await page.addInitScript(
    ({ at }) =>
      localStorage.setItem(
        "keiba_dashboard_auth_v1",
        JSON.stringify({
          userToken: "monitor-test",
          issuedAt: at,
          expiresIn: 900,
          serviceToken: null,
          useServiceToken: false,
        }),
      ),
    { at },
  );
  const points = Array.from({ length: 180 }, (_, i) => {
    const values = {
      cpu_percent: 28 + Math.sin(i / 9) * 12,
      memory_percent: 48 + Math.sin(i / 22) * 4,
      disk_percent: 38 + i / 500,
      net_rx_bytes_sec: 50_000 + Math.sin(i / 5) * 30_000,
      net_tx_bytes_sec: 15_000 + Math.sin(i / 12) * 5_000,
      disk_read_bytes_sec: 1024 * 50,
      disk_write_bytes_sec: 1024 * (20 + Math.sin(i / 3) * 10),
    };
    return {
      at: new Date(now.getTime() - (180 - i) * 10_000).toISOString(),
      values,
      max_values: values,
      sample_counts: {},
    };
  });
  let offline = false;
  await page.route("**/api/system/**", async (route) => {
    if (offline) return route.fulfill({ status: 503, json: { error: { message: "offline" } } });
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/history"))
      return route.fulfill({
        json: {
          host_id: "keiba-pc",
          start: new Date(
            now.getTime() - Number(url.searchParams.get("hours") ?? 1) * 3600_000,
          ).toISOString(),
          end: at,
          resolution_sec: 10,
          points: empty ? [] : points,
        },
      });
    if (url.pathname.endsWith("/events")) return route.fulfill({ json: { items: [] } });
    return route.fulfill({
      json: {
        status: empty ? "unknown" : "ok",
        age_sec: empty ? null : 2,
        sample: empty
          ? null
          : {
              host_id: "keiba-pc",
              hostname: "keiba-pc",
              scope: "host",
              sampled_at: at,
              uptime_sec: 105000,
              cpu_count: 8,
              cpu_percent: 32.8,
              cpu_per_core: [12, 25, 40, 52, 30, 28, 45, 30],
              memory_total_bytes: 16 * 1024 ** 3,
              memory_available_bytes: 8.3 * 1024 ** 3,
              memory_percent: 48.1,
              swap_total_bytes: 0,
              swap_used_bytes: 0,
              temperature_c: 43.2,
              disks: [
                {
                  path: "/",
                  label: "OS / 取得データ / DB",
                  total_bytes: 512 * 1024 ** 3,
                  used_bytes: 194 * 1024 ** 3,
                  available_bytes: 318 * 1024 ** 3,
                  percent: 38,
                },
              ],
              errors: [],
            },
        alerts: [],
        server_time: at,
        thresholds: { cpu: [80, 95], memory: [80, 90], disk: [80, 90] },
      },
    });
  });
  await page.route("**/api/scrape/status", (route) =>
    route.fulfill({
      json: {
        connection: "ok",
        workers: [{ name: "scheduler", alive: true, heartbeat_at: at, age_sec: 2 }],
        schedule: { enabled: true, baba_codes: [20] },
        running: [],
        progress: {
          total: 100,
          completed: 64,
          counts: { success: 60, skipped: 4, running: 1, planned: 33, retrying: 2 },
          next_at: at,
          plan_available: true,
        },
        sync: { last_status: "success", last_synced_at: at, next_scheduled_at: null },
      },
    }),
  );
  await page.route("**/api/scrape/jobs?**", (route) =>
    route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 30 } }),
  );
  return {
    goOffline: () => {
      offline = true;
    },
  };
}

test("monitor shows graphs, switches periods, and supports keyboard inspection", async ({
  page,
}) => {
  await monitorFixture(page);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/scrape/status");
  await expect(page.getByRole("heading", { name: "スクレイピング・PC稼働状況" })).toBeVisible();
  const graph = page.getByRole("img", { name: /CPU使用率の推移グラフ/ });
  await expect(graph).toBeVisible();
  await expect(graph.locator("path")).toHaveCount(1);
  await expect(page.getByRole("img", { name: /本日の取得進捗 64/ })).toBeVisible();
  await graph.focus();
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator(".monitorChartReadout").first()).toContainText("CPU:");
  const historyResponse = page.waitForResponse((response) =>
    response.url().includes("history?hours=24"),
  );
  await page.getByRole("button", { name: "24時間", exact: true }).click();
  await historyResponse;
  await page.getByLabel("グラフ集計方法").selectOption("max");
  await expect(page.locator(".monitorChart").first()).toContainText("区間最大");
  await page.getByRole("button", { name: "1時間", exact: true }).click();
  await page.setViewportSize({ width: 1440, height: 1100 });
  await page.screenshot({ path: "/tmp/keiba-monitor-desktop.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: "/tmp/keiba-monitor-mobile.png", fullPage: true });
  expect(
    await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),
  ).toBeTruthy();
  expect(errors).toEqual([]);
});

test("missing data stays empty and failed refresh retains last reading with a warning", async ({
  page,
}) => {
  const fixture = await monitorFixture(page, true);
  await page.goto("/scrape/status");
  await expect(page.getByText("計測データを待っています")).toBeVisible();
  await expect(page.getByText("計測データがありません").first()).toBeVisible();
  await expect(
    page.getByRole("img", { name: /CPU使用率の推移グラフ/ }).locator("path"),
  ).toHaveCount(0);
  fixture.goOffline();
  await page.getByRole("button", { name: "更新", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText("最新情報を取得できません");
});
