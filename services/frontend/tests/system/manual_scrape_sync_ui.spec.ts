import { expect, test } from "@playwright/test";

function uniqueUser(prefix = "system-sync") {
  const ts = Date.now();
  return {
    username: `${prefix}-${ts}`,
    password: "pass12345",
  };
}

async function getUserToken(page: any): Promise<string> {
  const raw = await page.evaluate(() => localStorage.getItem("keiba_dashboard_auth_v1"));
  if (!raw) throw new Error("auth storage missing");
  const parsed = JSON.parse(raw) as { userToken?: string | null };
  if (!parsed.userToken) throw new Error("userToken missing in storage");
  return parsed.userToken;
}

async function apiGetJson(page: any, path: string, token: string) {
  const res = await page.request.get(path, {
    headers: { Authorization: `Bearer ${token}` },
  });
  return { status: res.status(), json: await res.json().catch(() => null) };
}

async function apiPostJson(page: any, path: string, token: string, body: any) {
  const res = await page.request.post(path, {
    headers: { Authorization: `Bearer ${token}` },
    data: body,
  });
  return { status: res.status(), json: await res.json().catch(() => null) };
}

async function waitForDataReady(page: any, token: string, raceDate: string, babaCode: number, raceNo: number) {
  const deadlineMs = Date.now() + 120_000;
  let lastErr: any = null;

  while (Date.now() < deadlineMs) {
    try {
      // 1) races list → get numeric race_id
      const racesResp = await apiGetJson(
        page,
        `/api/races?race_date=${encodeURIComponent(raceDate)}&baba_code=${babaCode}&page=1&page_size=200`,
        token,
      );
      if (racesResp.status !== 200 || !racesResp.json?.items) {
        lastErr = racesResp;
        await page.waitForTimeout(5_000);
        continue;
      }

      const items = racesResp.json.items as any[];
      const race = items.find((r) => Number(r?.race_key?.race_no) === raceNo);
      if (!race?.race_id) {
        lastErr = { msg: "race not found yet", races: items.map((r) => r?.race_key) };
        await page.waitForTimeout(5_000);
        continue;
      }

      const raceId = Number(race.race_id);

      // 2) entries count
      const entriesResp = await apiGetJson(page, `/api/races/${raceId}/entries`, token);
      if (entriesResp.status !== 200 || !entriesResp.json?.items) {
        lastErr = entriesResp;
        await page.waitForTimeout(5_000);
        continue;
      }
      const entries = entriesResp.json.items as any[];
      if (entries.length !== 12) {
        lastErr = { msg: "entries not ready", got: entries.length };
        await page.waitForTimeout(5_000);
        continue;
      }

      // 3) odds counts (final)
      const checks: Array<{ betType: string; expected: number }> = [
        { betType: "tansho", expected: 12 },
        { betType: "fukusho", expected: 12 },
        { betType: "wakuren", expected: 32 },
        { betType: "umaren", expected: 66 },
        { betType: "umatan", expected: 132 },
        { betType: "wide", expected: 66 },
      ];

      for (const c of checks) {
        const oddsResp = await apiGetJson(
          page,
          `/api/races/${raceId}/odds?snapshot_kind=final&bet_type=${encodeURIComponent(c.betType)}`,
          token,
        );
        if (oddsResp.status !== 200 || !oddsResp.json?.items) {
          lastErr = { betType: c.betType, oddsResp };
          throw new Error("odds not ready");
        }
        const n = (oddsResp.json.items as any[]).length;
        if (n !== c.expected) {
          lastErr = { betType: c.betType, got: n, expected: c.expected };
          throw new Error("odds count mismatch");
        }
      }

      return { raceId };
    } catch {
      await page.waitForTimeout(5_000);
      continue;
    }
  }

  throw new Error(`data not ready in time: ${JSON.stringify(lastErr)}`);
}

test("manual scrape → sync → API count verification → UI display (system)", async ({ page }) => {
  test.setTimeout(180_000);

  // Target: Sonoda (baba=27), 2026-01-02, 1R
  const babaCode = 27;
  const raceDate = "2026-01-02";
  const raceNo = 1;

  const u = uniqueUser("system-scrape-sync");

  // Register (creates user + logs in)
  await page.goto("/register");
  await page.getByLabel("Username").fill(u.username);
  await page.getByLabel("Password", { exact: true }).fill(u.password);
  await page.getByLabel("Confirm password").fill(u.password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

  // Manual scrape request via UI (frontend→api→scraper)
  await page.goto("/scrape");
  await expect(page.getByRole("heading", { name: "Manual Scrape Task" })).toBeVisible();
  await page.getByLabel("baba_code (required)").fill(String(babaCode));
  await page.getByLabel("race_date (optional)").fill(raceDate);
  await page.getByLabel("race_no (optional)").fill(String(raceNo));
  await page.getByLabel("reason (optional)").fill("system-scrape-sync-test");

  // Retry if Pi busy (409)
  let accepted = false;
  for (let i = 0; i < 3; i++) {
    await page.getByRole("button", { name: "Request" }).click();
    const ok = page.getByText("task_id:", { exact: false });
    const conflict = page.getByText("scraper is busy (status=409)", { exact: false });
    const anyAlert = page.locator(".alert");

    await Promise.race([
      ok.waitFor({ state: "visible", timeout: 25_000 }),
      anyAlert.first().waitFor({ state: "visible", timeout: 25_000 }),
    ]);

    if (await ok.isVisible()) {
      accepted = true;
      break;
    }
    if (await conflict.isVisible()) {
      await page.waitForTimeout(5_000);
      continue;
    }

    // other errors should fail
    await expect(page.locator(".alert")).toHaveCount(0);
  }

  if (!accepted) {
    // Environment-dependent (Pi busy)
    test.skip(true, "scraper is busy; skip system scrape-sync test");
  }

  const token = await getUserToken(page);

  // Trigger sync (Pi → PC pull)
  const syncResp = await apiPostJson(page, "/api/scrape/sync", token, {});
  // 202 accepted is typical; 200/409 can happen depending on implementation/state.
  expect([200, 202, 409]).toContain(syncResp.status);

  // Wait until API reflects the scraped data fully
  const { raceId } = await waitForDataReady(page, token, raceDate, babaCode, raceNo);

  // UI confirmation: Races → Race Detail → Entries & Odds tabs show expected counts
  await page.goto("/races");
  await expect(page.getByRole("heading", { name: "Races" })).toBeVisible();
  await page.getByLabel("race_date").fill(raceDate);
  await page.getByLabel("baba_code (optional)").selectOption(String(babaCode));
  await page.getByRole("button", { name: "Search" }).click();

  await expect(page.getByRole("link", { name: String(raceId) })).toBeVisible();
  await page.getByRole("link", { name: String(raceId) }).click();
  await expect(page.getByRole("heading", { name: "Race Detail" })).toBeVisible();

  // Entries
  await page.getByRole("button", { name: "entries" }).click();
  await expect(page.locator("table.table tbody tr")).toHaveCount(12);

  // Odds counts (title includes items=...)
  await page.getByRole("button", { name: "odds" }).click();

  const oddsChecks: Array<{ betType: string; expected: number }> = [
    { betType: "tansho", expected: 12 },
    { betType: "fukusho", expected: 12 },
    { betType: "wakuren", expected: 32 },
    { betType: "umaren", expected: 66 },
    { betType: "umatan", expected: 132 },
    { betType: "wide", expected: 66 },
  ];

  for (const c of oddsChecks) {
    await page.getByLabel("snapshot_kind").selectOption("final");
    await page.getByLabel("bet_type").selectOption(c.betType);
    await page.getByRole("button", { name: "Fetch odds" }).click();
    await expect(page.getByText(new RegExp(`items=${c.expected}\\b`))).toBeVisible();
  }

  // Ensure we didn't end up with an error box at the end.
  await expect(page.locator(".alert")).toHaveCount(0);
});






