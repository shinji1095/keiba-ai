import { expect, test } from "@playwright/test";

const testManifest = {
  races: [
    {
      race_id: "27_2026-01-02_01R",
      race_date: "2026-01-02",
      baba_code: 27,
      race_no: 1,
      venue_name: "園田",
      files: [
        { name: "01_debatable_normalized.md", title: "出馬表（正規化）", description: "test desc" },
        { name: "02_odds_tanfuku.md", title: "単勝・複勝オッズ（最終）", description: "test desc" },
      ],
    },
  ],
};

const sampleMarkdown = `# Test Heading

## Table Example

| col1 | col2 |
|---|---|
| A | B |
| C | D |

Normal text line.
`;

async function setAuthStorage(page: any, token = "test-token") {
  const value = JSON.stringify({
    userToken: token,
    issuedAt: new Date().toISOString(),
    expiresIn: 900,
    serviceToken: null,
    useServiceToken: false,
  });
  await page.addInitScript((storageValue: string) => {
    localStorage.setItem("keiba_dashboard_auth_v1", storageValue);
  }, value);
}

test("test data viewer shows races and files", async ({ page }) => {
  await setAuthStorage(page);

  await page.route("**/docs/test/data/manifest.json", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(testManifest),
    });
  });

  await page.route("**/docs/test/data/27_2026-01-02_01R/01_debatable_normalized.md", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "text/markdown",
      body: sampleMarkdown,
    });
  });

  await page.goto("/test-data");

  await expect(page.getByRole("heading", { name: "Test Data Viewer" })).toBeVisible();
  await expect(page.getByText("園田 2026-01-02 1R")).toBeVisible();

  await page.getByRole("button", { name: "園田 2026-01-02 1R" }).click();
  await expect(page.getByRole("button", { name: "出馬表（正規化）" })).toBeVisible();

  await page.getByRole("button", { name: "出馬表（正規化）" }).click();
  await expect(page.getByText("Test Heading")).toBeVisible();
  await expect(page.getByRole("cell", { name: "A", exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "D", exact: true })).toBeVisible();
});




