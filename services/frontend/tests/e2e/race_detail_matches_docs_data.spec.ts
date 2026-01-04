import { expect, test, type Page } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

function tokenResponse() {
  return {
    access_token: "test-token",
    token_type: "Bearer" as const,
    expires_in: 900,
    issued_at: new Date().toISOString(),
  };
}

function authStorageValue(token: string, issuedAt: string, expiresIn: number): string {
  return JSON.stringify({
    userToken: token,
    issuedAt,
    expiresIn,
    serviceToken: null,
    useServiceToken: false,
  });
}

async function setAuthStorage(page: Page, token = "test-token") {
  const tr = tokenResponse();
  const value = authStorageValue(token, tr.issued_at, tr.expires_in);
  await page.addInitScript((storageValue: string) => {
    localStorage.setItem("keiba_dashboard_auth_v1", storageValue);
  }, value);
}

type Row = Record<string, string>;

function parseMarkdownTable(md: string, heading: string): Row[] {
  const idx = md.indexOf(heading);
  if (idx < 0) throw new Error(`heading not found: ${heading}`);
  const after = md.slice(idx + heading.length);
  const lines = after.split("\n").map((l) => l.trimEnd());

  // find first table header row
  let headerLineIdx = lines.findIndex((l) => l.startsWith("|") && l.includes("|"));
  while (headerLineIdx >= 0 && headerLineIdx < lines.length) {
    const header = lines[headerLineIdx];
    const sep = lines[headerLineIdx + 1] || "";
    if (sep.startsWith("|") && sep.includes("---")) break;
    headerLineIdx = lines.findIndex((l, i) => i > headerLineIdx && l.startsWith("|"));
  }
  if (headerLineIdx < 0) throw new Error(`table not found after heading: ${heading}`);

  const headers = headerSplit(lines[headerLineIdx]);
  const out: Row[] = [];
  for (let i = headerLineIdx + 2; i < lines.length; i++) {
    const l = lines[i];
    if (!l.startsWith("|")) break;
    const cols = headerSplit(l);
    if (cols.length !== headers.length) continue;
    const row: Row = {};
    headers.forEach((h, j) => (row[h] = cols[j]));
    out.push(row);
  }
  return out;
}

function headerSplit(line: string): string[] {
  return line
    .split("|")
    .slice(1, -1)
    .map((c) => c.trim());
}

function toNum(s: string): number | null {
  const t = s.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

function legsFromStr(s: string): number[] {
  return s
    .split("-")
    .map((x) => x.trim())
    .filter(Boolean)
    .map((x) => Number(x));
}

test("Sonoda 2026-01-02 1R: UI values match docs/test/data (tansho/fukusho/results/payouts)", async ({ page }) => {
  const raceDate = "2026-01-02";
  const babaCode = 27;
  const raceId = 1;

  const repoRoot = path.resolve(__dirname, "../../..", ".."); // services/frontend/tests/e2e -> repo root
  const dataDir = path.join(repoRoot, "docs", "test", "data", "27_2026-01-02_01R");

  const mdOdds = await fs.readFile(path.join(dataDir, "02_odds_tanfuku.md"), "utf-8");
  const mdResults = await fs.readFile(path.join(dataDir, "07_race_results.md"), "utf-8");
  const mdPayouts = await fs.readFile(path.join(dataDir, "08_payouts.md"), "utf-8");

  const oddsRows = parseMarkdownTable(mdOdds, "## odds_tanfuku_final");
  const resultsRows = parseMarkdownTable(mdResults, "## race_results");
  const payoutsRows = parseMarkdownTable(mdPayouts, "## payouts");

  await setAuthStorage(page);

  // Minimal routes: venues/races + detail/entries + odds/results/payouts from docs
  await page.route("**/api/venues", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [{ baba_code: babaCode, venue_name: "園田" }] }),
    });
  });

  await page.route("**/api/races**", async (route) => {
    const url = route.request().url();
    if (url.includes("/api/races?")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              race_id: raceId,
              race_key: { race_date: raceDate, baba_code: babaCode, race_no: 1 },
              start_time: "10:40",
              race_name: "Ｃ３三４歳以上",
              status: "finished",
            },
          ],
          page: 1,
          page_size: 200,
        }),
      });
      return;
    }

    if (url.endsWith(`/api/races/${raceId}`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          race_id: raceId,
          race_key: { race_date: raceDate, baba_code: babaCode, race_no: 1 },
          start_time: "10:40",
          distance_m: 1400,
          course: "右",
          weather: "晴",
          track_condition: "良",
          race_name: "Ｃ３三４歳以上",
          field_size: 12,
          status: "finished",
        }),
      });
      return;
    }

    if (url.endsWith(`/api/races/${raceId}/entries`)) {
      const items = oddsRows.map((r, i) => ({
        race_entry_id: i + 1,
        race_id: raceId,
        post_position: Number(r["waku"]) || null,
        horse_number: Number(r["horse_no"]),
        horse_name: r["horse_name"],
        jockey_name: r["jockey_name"] || null,
        trainer_name: r["trainer_name"] || null,
        handicap_kg: toNum(r["burden_weight"]),
        body_weight: toNum(r["body_weight"]),
        body_weight_diff: toNum(r["body_weight_diff"]),
      }));
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items }) });
      return;
    }

    if (url.includes(`/api/races/${raceId}/odds?`)) {
      const u = new URL(url);
      const betType = u.searchParams.get("bet_type") || "tansho";
      const snapshotKind = u.searchParams.get("snapshot_kind") || "final";

      const items =
        betType === "tansho"
          ? oddsRows.map((r, i) => ({
              odds_item_id: i + 1,
              odds_snapshot_id: 10,
              legs: [Number(r["horse_no"])],
              is_ordered: false,
              odds_min: toNum(r["win_odds"]),
              odds_max: toNum(r["win_odds"]),
              popularity: null,
              raw_text: null,
            }))
          : betType === "fukusho"
            ? oddsRows.map((r, i) => ({
                odds_item_id: i + 1,
                odds_snapshot_id: 11,
                legs: [Number(r["horse_no"])],
                is_ordered: false,
                odds_min: toNum(r["place_odds_min"]),
                odds_max: toNum(r["place_odds_max"]),
                popularity: null,
                raw_text: null,
              }))
            : [];

      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          snapshot: {
            odds_snapshot_id: 10,
            race_id: raceId,
            bet_type: betType,
            snapshot_kind: snapshotKind,
            captured_at: new Date().toISOString(),
            source_url: "https://www.keiba.go.jp/KeibaWeb/TodayRaceInfo/OddsTanFuku",
            odds_flg: null,
            is_final: snapshotKind === "final",
          },
          items,
        }),
      });
      return;
    }

    if (url.endsWith(`/api/races/${raceId}/results`)) {
      const items = resultsRows.map((r, i) => ({
        race_result_id: i + 1,
        race_id: raceId,
        finish_position: Number(r["finish_position"]),
        horse_number: Number(r["horse_no"]),
        time_str: r["time_str"] || null,
        margin: r["margin"] || null,
        last3f: toNum(r["last3f"]),
        popularity: toNum(r["popularity"]),
        corner1: null,
        corner2: null,
        corner3: null,
        corner4: null,
      }));
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items }) });
      return;
    }

    if (url.endsWith(`/api/races/${raceId}/payouts`)) {
      const items = payoutsRows.map((r, i) => {
        const legs = legsFromStr(r["legs"]);
        const isOrdered = r["bet_type"] === "umatan" || r["bet_type"] === "sanrentan";
        return {
          payout_id: i + 1,
          race_id: raceId,
          bet_type: r["bet_type"],
          legs,
          is_ordered: isOrdered,
          payout_yen: Number(r["payout_yen"]),
          popularity: toNum(r["popularity"]),
        };
      });
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items }) });
      return;
    }

    await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  });

  // Navigate to Race Detail
  await page.goto("/races");
  await page.getByLabel("race_date").fill(raceDate);
  await page.getByLabel("baba_code (optional)").selectOption(String(babaCode));
  await page.getByRole("button", { name: "Search" }).click();
  await page.getByRole("link", { name: String(raceId) }).click();
  await expect(page.getByRole("heading", { name: "Race Detail" })).toBeVisible();

  // odds tansho: check all 12 horses values match docs
  await page.getByRole("button", { name: "odds" }).click();
  await page.getByLabel("snapshot_kind").selectOption("final");
  await page.getByLabel("bet_type").selectOption("tansho");
  await page.getByRole("button", { name: "Fetch odds" }).click();
  for (const r of oddsRows) {
    const horseNo = r["horse_no"];
    const win = r["win_odds"];
    const row = page.locator("table.table tbody tr", { hasText: horseNo });
    await expect(row).toContainText(win);
  }

  // odds fukusho: check all 12 horses min/max match docs
  await page.getByLabel("bet_type").selectOption("fukusho");
  await page.getByRole("button", { name: "Fetch odds" }).click();
  for (const r of oddsRows) {
    const horseNo = r["horse_no"];
    const mn = r["place_odds_min"];
    const mx = r["place_odds_max"];
    const row = page.locator("table.table tbody tr", { hasText: horseNo });
    await expect(row).toContainText(mn);
    await expect(row).toContainText(mx);
  }

  // results: verify time_str per horse_no matches docs (spot-check all rows)
  await page.getByRole("button", { name: "results" }).click();
  for (const r of resultsRows) {
    const horseNo = r["horse_no"];
    const timeStr = r["time_str"];
    if (!timeStr) continue;
    const row = page.locator("table.table tbody tr", { hasText: horseNo });
    await expect(row).toContainText(timeStr);
  }

  // payouts: verify key payouts exist exactly as docs (subset)
  await page.getByRole("button", { name: "payouts" }).click();
  // tansho 8 110 / umatan 8-11 4350 / sanrentan 8-11-9 8830
  await expect(page.getByText("tansho")).toBeVisible();
  await expect(page.getByText("110")).toBeVisible();
  await expect(page.getByText("8-11")).toBeVisible();
  await expect(page.getByText("4350")).toBeVisible();
  await expect(page.getByText("8-11-9")).toBeVisible();
  await expect(page.getByText("8830")).toBeVisible();
});


