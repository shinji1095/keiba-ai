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
  await expect(page.getByText("updated_at:")).toBeVisible();

  // Ensure we didn't end up with an error box.
  await expect(page.locator(".alert")).toHaveCount(0);
});


