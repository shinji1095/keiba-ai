import { expect, test, type Page } from "@playwright/test";

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

function genOddsItems(betType: string): any[] {
  const nByType: Record<string, number> = {
    tansho: 12,
    fukusho: 12,
    wakuren: 32,
    wakutan: 0, // 例: 枠単が提供されない場合もある（UIは空でも表示できること）
    umaren: 66,
    umatan: 132,
    wide: 66,
  };
  const n = nByType[betType] ?? 0;
  const items: any[] = [];
  for (let i = 0; i < n; i++) {
    const a = (i % 12) + 1;
    const b = ((i + 1) % 12) + 1;
    const legs = betType === "tansho" || betType === "fukusho" ? [a] : [Math.min(a, b), Math.max(a, b)];
    items.push({
      odds_item_id: i + 1,
      odds_snapshot_id: 10,
      legs,
      is_ordered: betType === "umatan" || betType === "wakutan",
      odds_min: 1.1 + i * 0.1,
      odds_max: betType === "wide" ? 1.2 + i * 0.1 : 1.1 + i * 0.1,
      popularity: i + 1,
      raw_text: null,
    });
  }
  return items;
}

test("Race Detail shows summary/entries/odds/results/payouts (all required)", async ({ page }) => {
  // Target: Sonoda 2026-01-02 1R (RaceMarkTable 相当の results/payouts を含む)
  const raceDate = "2026-01-02";
  const babaCode = 27;
  const raceId = 1;

  await setAuthStorage(page);

  await page.route("**/api/venues", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [{ baba_code: babaCode, venue_name: "園田" }] }),
    });
  });

  await page.route("**/api/spec/race-cards/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        race: {
          race_id: `${babaCode}_${raceDate}_01`,
          race_date: raceDate,
          baba_code: babaCode,
          race_no: 1,
          post_time: "10:40:00",
          race_name: "Ｃ３三４歳以上",
          surface: "ダート",
          distance_m: 1400,
          direction: "右",
          weather: "晴",
          track_condition: "良",
        },
        persons: [],
        horses: [{ horse_id: 101, name: "Horse-1", sex: "牝", age: 7 }],
        race_entries: [
          {
            race_id: `${babaCode}_${raceDate}_01`,
            horse_no: 1,
            waku: 1,
            horse_id: 101,
            burden_weight_display: 55.0,
            apprentice_allowance_symbol: null,
            apprentice_allowance_kg: null,
            burden_weight_base: 55.0,
            body_weight: 458,
            body_weight_diff: 1,
            win_odds: 17.2,
            popularity: 3,
            jockey_person_id: null,
            trainer_person_id: null,
            owner_person_id: null,
            perf_total_id: 1,
            perf_dirt_left_id: 1,
            perf_dirt_right_id: 1,
            perf_track_id: 1,
            perf_distance_id: 1,
            best_time_id: 1,
          },
        ],
        perf_total: [{ horse_id: 101, first_cnt: 1, second_cnt: 5, third_cnt: 4, out_cnt: 8, starts: 18 }],
        perf_dirt_left: [{ horse_id: 101, first_cnt: 0, second_cnt: 0, third_cnt: 0, out_cnt: 0, starts: 0 }],
        perf_dirt_right: [{ horse_id: 101, first_cnt: 1, second_cnt: 5, third_cnt: 4, out_cnt: 8, starts: 18 }],
        perf_track: [{ horse_id: 101, first_cnt: 1, second_cnt: 5, third_cnt: 4, out_cnt: 8, starts: 18 }],
        perf_distance: [{ horse_id: 101, first_cnt: 1, second_cnt: 5, third_cnt: 4, out_cnt: 8, starts: 18 }],
        best_time: [
          {
            horse_id: 101,
            baba_code: babaCode,
            surface: "ダート",
            distance_m: 1400,
            best_time_sec: 92.9,
            best_time_good_sec: 92.9,
            best_time_raw: "1:32.9",
            best_time_good_raw: "1:32.9",
          },
        ],
        last5: [
          {
            race_id: `${babaCode}_${raceDate}_01`,
            horse_no: 1,
            order_in_last5: 1,
            finish_pos: 4,
            past_race_date: "2025-12-17",
            track_condition: "良",
            runners: 10,
            place: "園田",
            direction: "右",
            distance_m: 1400,
            horse_no_in_race: 1,
            popularity: 3,
            body_weight: 457,
            jockey_name: "廣瀬航",
            burden_weight: 55.0,
            time_raw: "1:36.0",
            time_sec: 96.0,
            passing_order_raw: "4-4-3-2",
            passing_order_arr: [4, 4, 3, 2],
            last3f: 42.4,
            time_diff: 0.8,
            winner_name: "イッシン",
          },
        ],
      }),
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
      const items = Array.from({ length: 12 }).map((_, i) => ({
        race_entry_id: i + 1,
        race_id: raceId,
        post_position: Math.floor(i / 2) + 1,
        horse_number: i + 1,
        horse_name: `Horse-${i + 1}`,
        jockey_name: `Jockey-${i + 1}`,
        trainer_name: `Trainer-${i + 1}`,
        handicap_kg: 55.0,
        body_weight: 450 + i,
        body_weight_diff: i % 2 === 0 ? 1 : -1,
      }));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items }),
      });
      return;
    }

    if (url.includes(`/api/races/${raceId}/odds?`)) {
      const u = new URL(url);
      const betType = u.searchParams.get("bet_type") || "tansho";
      const snapshotKind = u.searchParams.get("snapshot_kind") || "final";
      const items = genOddsItems(betType);
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
      // RaceMarkTable 由来想定の最低限
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              race_result_id: 1,
              race_id: raceId,
              finish_position: 1,
              horse_number: 8,
              time_str: "1:34.4",
              margin: null,
              last3f: 41.2,
              popularity: 1,
              corner1: "9,10,12,3,6,8,7,1,11,4,5,2",
              corner2: "9,10,12,3,6,8,7,1,11,4,5,2",
              corner3: "9,8,12,10,6,7,1,11,3,2,4,5",
              corner4: "8,9,12,6,10,11,1,2,7,4,3,5",
            },
          ],
        }),
      });
      return;
    }

    if (url.endsWith(`/api/races/${raceId}/payouts`)) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            { payout_id: 1, race_id: raceId, bet_type: "tansho", legs: [8], is_ordered: false, payout_yen: 110, popularity: 1 },
            { payout_id: 2, race_id: raceId, bet_type: "umatan", legs: [8, 11], is_ordered: true, payout_yen: 4350, popularity: 11 },
          ],
        }),
      });
      return;
    }

    await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  });

  // Races → filter → Race Detail
  await page.goto("/races");
  await expect(page.getByRole("heading", { name: "Races" })).toBeVisible();
  await page.getByLabel("race_date").fill(raceDate);
  await page.getByLabel("baba_code (optional)").selectOption(String(babaCode));
  await page.getByRole("button", { name: "Search" }).click();
  await expect(page.getByText("Ｃ３三４歳以上")).toBeVisible();

  await page.getByRole("link", { name: String(raceId) }).click();
  await expect(page.getByRole("heading", { name: "Race Detail" })).toBeVisible();

  // summary (default)
  await expect(page.getByText(`race_id=${raceId}`)).toBeVisible();
  await expect(page.getByText("distance 1400")).toBeVisible();

  // entries
  await page.getByRole("button", { name: "entries" }).click();
  await expect(page.locator("table.table tbody tr")).toHaveCount(12);
  await expect(page.getByRole("cell", { name: "Horse-1", exact: true })).toBeVisible();
  await expect(page.getByText("1-5-4-8 (18)")).toBeVisible();

  // entries: expand details for horse 1 (spec last5/perf)
  await page.locator("table.table tbody tr").first().getByRole("button", { name: "+" }).click();
  await expect(page.getByText("着別成績 / 競走成績（直近5走）")).toBeVisible();
  await expect(page.getByText("1:36.0")).toBeVisible();

  // odds: verify each required bet_type shows items count
  await page.getByRole("button", { name: "odds" }).click();
  const oddsChecks: Array<{ betType: string; expected: number }> = [
    { betType: "tansho", expected: 12 },
    { betType: "fukusho", expected: 12 },
    { betType: "wakuren", expected: 32 },
    { betType: "wakutan", expected: 0 },
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

  // results (RaceMarkTable)
  await page.getByRole("button", { name: "results" }).click();
  await expect(page.getByText("1:34.4")).toBeVisible();

  // payouts (RaceMarkTable)
  await page.getByRole("button", { name: "payouts" }).click();
  await expect(page.getByText("tansho")).toBeVisible();
  await expect(page.getByText("110")).toBeVisible();

  // no global error boxes
  await expect(page.locator(".alert")).toHaveCount(0);
});




