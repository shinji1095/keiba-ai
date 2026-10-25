import { expect, test } from "@playwright/test";

function uniqueUser(prefix = "system") {
  const ts = Date.now();
  return {
    username: `${prefix}-${ts}`,
    password: "pass12345",
  };
}

test("scrape schedule is visible via reverse-proxy (frontend→api→scraper)", async ({ page }) => {
  const u = uniqueUser();

  // Register (creates user + logs in)
  await page.goto("/register");
  await page.getByLabel("ユーザー名").fill(u.username);
  await page.getByLabel("パスワード", { exact: true }).fill(u.password);
  await page.getByLabel("パスワード（確認）").fill(u.password);
  await page.getByRole("button", { name: "登録する" }).click();

  await expect(page.getByRole("heading", { name: "ホーム" })).toBeVisible();

  // Open scrape console and ensure schedule loaded (requires api→scraper reachability)
  await page.goto("/scrape");
  await expect(page.getByRole("heading", { name: "データ収集" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "自動収集の設定" })).toBeVisible();

  // Once schedule is fetched successfully, it shows updated_at.
  // Use a regex to avoid matching "last_synced_at:".
  await expect(page.getByText(/^設定更新日時：/)).toBeVisible();

  // Ensure we didn't end up with an error box.
  await expect(page.locator(".alert")).toHaveCount(0);
});

test("manual scrape task can be requested via reverse-proxy (frontend→api→scraper)", async ({ page }) => {
  const u = uniqueUser("system-manual");

  // Register (creates user + logs in)
  await page.goto("/register");
  await page.getByLabel("ユーザー名").fill(u.username);
  await page.getByLabel("パスワード", { exact: true }).fill(u.password);
  await page.getByLabel("パスワード（確認）").fill(u.password);
  await page.getByRole("button", { name: "登録する" }).click();

  await expect(page.getByRole("heading", { name: "ホーム" })).toBeVisible();

  await page.goto("/scrape");
  await expect(page.getByRole("heading", { name: "データ収集" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "手動収集" })).toBeVisible();

  await page.getByLabel("競馬場コード（必須）").fill("32");
  await page.getByLabel("開催日（任意）").fill("2025-12-28");
  await page.getByLabel("レース番号（任意）").fill("1");
  await page.getByLabel("依頼理由（任意）").fill("system-test");

  // The PC-local scraper may be busy; retry a couple times if we hit 409 conflict.
  for (let i = 0; i < 3; i++) {
    await page.getByRole("button", { name: "収集を依頼" }).click();
    const accepted = page.getByText("収集依頼ID：", { exact: false });
    const conflict = page.getByText("収集処理が実行中です。", { exact: false });
    const anyAlert = page.locator(".alert");

    // Wait for either success (task_id shown) or error alert.
    await Promise.race([
      accepted.waitFor({ state: "visible", timeout: 20_000 }),
      anyAlert.first().waitFor({ state: "visible", timeout: 20_000 }),
    ]);

    if (await accepted.isVisible()) {
      const manualCard = page.locator(".card", {
        has: page.getByRole("heading", { name: "手動収集" }),
      });
      await expect(page.getByText("収集依頼ID：")).toBeVisible();
      await expect(page.getByText("受付日時：")).toBeVisible();
      await expect(manualCard.locator(".pill.ok", { hasText: "受付済み" })).toBeVisible();
      return;
    }

    if (await conflict.isVisible()) {
      // give the running job a little time and retry
      await page.waitForTimeout(5_000);
      continue;
    }

    // Other errors (e.g. 502) should fail the test.
    await expect(page.locator(".alert")).toHaveCount(0);
  }

  // If we only hit "busy", fail with a clear message.
  await expect(page.getByText("収集処理が実行中です。", { exact: false })).toHaveCount(0);
});


