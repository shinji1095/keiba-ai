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
  await page.getByLabel("Username").fill(u.username);
  await page.getByLabel("Password", { exact: true }).fill(u.password);
  await page.getByLabel("Confirm password").fill(u.password);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

  // Open scrape console and ensure schedule loaded (requires api→scraper reachability)
  await page.goto("/scrape");
  await expect(page.getByRole("heading", { name: "Scrape Console" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Scrape Schedule" })).toBeVisible();

  // Once schedule is fetched successfully, it shows updated_at.
  // Use a regex to avoid matching "last_synced_at:".
  await expect(page.getByText(/^updated_at:/)).toBeVisible();

  // Ensure we didn't end up with an error box.
  await expect(page.locator(".alert")).toHaveCount(0);
});

test("manual scrape task can be requested via reverse-proxy (frontend→api→scraper)", async ({ page }) => {
  const u = uniqueUser("system-manual");

  // Register (creates user + logs in)
  await page.goto("/register");
  await page.getByLabel("Username").fill(u.username);
  await page.getByLabel("Password", { exact: true }).fill(u.password);
  await page.getByLabel("Confirm password").fill(u.password);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

  await page.goto("/scrape");
  await expect(page.getByRole("heading", { name: "Scrape Console" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Manual Scrape Task" })).toBeVisible();

  await page.getByLabel("baba_code (required)").fill("32");
  await page.getByLabel("race_date (optional)").fill("2025-12-28");
  await page.getByLabel("race_no (optional)").fill("1");
  await page.getByLabel("reason (optional)").fill("system-test");

  // The Pi scraper may be busy; retry a couple times if we hit 409 conflict.
  for (let i = 0; i < 3; i++) {
    await page.getByRole("button", { name: "Request" }).click();
    const accepted = page.getByText("task_id:", { exact: false });
    const conflict = page.getByText("scraper is busy (status=409)", { exact: false });
    const anyAlert = page.locator(".alert");

    // Wait for either success (task_id shown) or error alert.
    await Promise.race([
      accepted.waitFor({ state: "visible", timeout: 20_000 }),
      anyAlert.first().waitFor({ state: "visible", timeout: 20_000 }),
    ]);

    if (await accepted.isVisible()) {
      const manualCard = page.locator(".card", {
        has: page.getByRole("heading", { name: "Manual Scrape Task" }),
      });
      await expect(page.getByText("task_id:")).toBeVisible();
      await expect(page.getByText("accepted_at:")).toBeVisible();
      await expect(manualCard.locator(".pill.ok", { hasText: "ACCEPTED" })).toBeVisible();
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
  await expect(page.getByText("scraper is busy", { exact: false })).toHaveCount(0);
});


