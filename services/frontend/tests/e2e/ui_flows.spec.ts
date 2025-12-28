import { expect, test, type Page } from "@playwright/test";

const tokenResponse = {
  access_token: "test-token",
  token_type: "Bearer",
  expires_in: 900,
  issued_at: "2025-12-28T00:00:00Z",
};

function authStorageValue(token: string): string {
  return JSON.stringify({
    userToken: token,
    issuedAt: tokenResponse.issued_at,
    expiresIn: tokenResponse.expires_in,
    serviceToken: null,
    useServiceToken: false,
  });
}

async function setAuthStorage(page: Page, token = tokenResponse.access_token) {
  const value = authStorageValue(token);
  await page.addInitScript((storageValue: string) => {
    localStorage.setItem("keiba_dashboard_auth_v1", storageValue);
  }, value);
}

async function stubHealth(page: Page) {
  await page.route("**/api/health", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "ok" }),
    });
  });
}

test("login success navigates to overview", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(tokenResponse),
    });
  });
  await stubHealth(page);

  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("adminpass");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("login failure shows error", async ({ page }) => {
  await page.route("**/api/auth/login", async (route) => {
    await route.fulfill({
      status: 401,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "invalid credentials" } }),
    });
  });

  await page.goto("/login");
  await page.getByLabel("Username").fill("admin");
  await page.getByLabel("Password").fill("wrong");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(page.locator(".alert")).toContainText("invalid credentials");
});

test("register success navigates to overview", async ({ page }) => {
  await page.route("**/api/auth/register", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(tokenResponse),
    });
  });
  await stubHealth(page);

  await page.goto("/register");
  await page.getByLabel("Username").fill("new-user");
  await page.getByLabel("Password").fill("pass123");
  await page.getByLabel("Confirm password").fill("pass123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
});

test("register failure shows error", async ({ page }) => {
  await page.route("**/api/auth/register", async (route) => {
    await route.fulfill({
      status: 400,
      contentType: "application/json",
      body: JSON.stringify({ error: { message: "registration failed" } }),
    });
  });

  await page.goto("/register");
  await page.getByLabel("Username").fill("new-user");
  await page.getByLabel("Password").fill("pass123");
  await page.getByLabel("Confirm password").fill("pass123");
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.locator(".alert")).toContainText("registration failed");
});

test("races list and detail show data", async ({ page }) => {
  await setAuthStorage(page);
  const today = new Date().toISOString().slice(0, 10);

  await page.route("**/api/venues", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ items: [{ baba_code: 1, venue_name: "Sample Venue" }] }),
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
              race_id: 1,
              race_key: { race_date: today, baba_code: 1, race_no: 1 },
              start_time: "12:00",
              race_name: "Sample Race",
              status: "scheduled",
            },
          ],
          page: 1,
          page_size: 200,
        }),
      });
      return;
    }

    if (url.endsWith("/api/races/1")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          race_id: 1,
          race_key: { race_date: today, baba_code: 1, race_no: 1 },
          start_time: "12:00",
          distance_m: 1200,
          course: "D",
          weather: "sunny",
          track_condition: "fast",
          race_name: "Sample Race",
          field_size: 12,
          status: "scheduled",
        }),
      });
      return;
    }

    if (url.endsWith("/api/races/1/entries")) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          items: [
            {
              race_entry_id: 1,
              race_id: 1,
              post_position: 1,
              horse_number: 1,
              horse_name: "Sample Horse",
            },
          ],
        }),
      });
      return;
    }

    await route.fulfill({ status: 404, contentType: "application/json", body: "{}" });
  });

  await page.goto("/races");
  await expect(page.getByRole("heading", { name: "Races" })).toBeVisible();
  await expect(page.getByText("Sample Race")).toBeVisible();

  await page.getByRole("link", { name: "1" }).click();
  await expect(page.getByRole("heading", { name: "Race Detail" })).toBeVisible();

  await page.getByRole("button", { name: "entries" }).click();
  await expect(page.getByText("Sample Horse")).toBeVisible();
});

test("oauth clients manage flow", async ({ page }) => {
  await setAuthStorage(page);
  const clients: any[] = [];
  const createdAt = "2025-12-28T00:00:00Z";

  await page.route(/\/api\/admin\/oauth-clients\/[^/]+\/rotate-secret$/, async (route) => {
    const url = new URL(route.request().url());
    const clientId = url.pathname.split("/").slice(-2, -1)[0];
    const existing = clients.find((c) => c.client_id === clientId);
    const payload = existing || {
      client_id: clientId,
      name: "scraper",
      scopes: ["scrape:write"],
      is_active: true,
      created_at: createdAt,
      revoked_at: null,
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ client: { ...payload, client_secret: "secret-rotated" } }),
    });
  });

  await page.route(/\/api\/admin\/oauth-clients\/[^/]+$/, async (route) => {
    if (route.request().method() === "DELETE") {
      const url = new URL(route.request().url());
      const clientId = url.pathname.split("/").pop();
      const idx = clients.findIndex((c) => c.client_id === clientId);
      if (idx >= 0) clients.splice(idx, 1);
      await route.fulfill({ status: 204, body: "" });
      return;
    }
    await route.fulfill({ status: 405, body: "" });
  });

  await page.route("**/api/admin/oauth-clients", async (route) => {
    const req = route.request();
    if (req.method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ items: clients, page: 1, page_size: 50 }),
      });
      return;
    }
    if (req.method() === "POST") {
      const body = req.postDataJSON();
      const clientId = `client-${clients.length + 1}`;
      const client = {
        client_id: clientId,
        name: body.name,
        scopes: body.scopes,
        is_active: body.is_active ?? true,
        created_at: createdAt,
        revoked_at: null,
      };
      clients.push(client);
      await route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ client: { ...client, client_secret: "secret-1" } }),
      });
      return;
    }
    await route.fulfill({ status: 405, body: "" });
  });

  await page.route("**/api/auth/token", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(tokenResponse),
    });
  });

  await page.goto("/admin/oauth-clients");

  await page.getByLabel("name").fill("scraper");
  await page.getByLabel("scopes", { exact: false }).fill("scrape:write");
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByText("client-1")).toBeVisible();
  await expect(page.getByText("Clients (1)")).toBeVisible();

  await page.getByRole("button", { name: "Rotate secret" }).click();
  await expect(page.getByText("secret-rotated")).toBeVisible();

  await page.getByLabel("client_id").fill("client-1");
  await page.getByLabel("client_secret").fill("secret-rotated");
  await page.getByRole("button", { name: "Issue token" }).click();
  await expect(page.getByText("access_token")).toBeVisible();

  await page.getByRole("button", { name: "Revoke" }).click();
  await expect(page.getByText("Clients (0)")).toBeVisible();
});

test("scrape console run shows response", async ({ page }) => {
  await setAuthStorage(page);
  await page.route("**/api/scrape/odds-snapshots", async (route) => {
    await route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({
        race_id: 1,
        bet_type: "tansho",
        snapshot_kind: "final",
        odds_snapshot_id: 10,
        num_items: 1,
      }),
    });
  });

  await page.goto("/scrape");
  await expect(page.getByRole("heading", { name: "Scrape Console" })).toBeVisible();

  await page.getByRole("button", { name: "Run" }).click();
  await expect(page.getByText("odds_snapshot_id")).toBeVisible();
});
