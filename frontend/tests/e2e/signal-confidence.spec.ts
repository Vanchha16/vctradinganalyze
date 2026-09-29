import { expect, type Page, test } from "@playwright/test";

import { E2E_ADMIN, login } from "./fixtures";

/** smc-ict-crt-v1 has no confidence score: the backend stores 0, meaning
 * "not applicable", and the Signals pages must say so instead of "0%".
 * A scored signal keeps its percentage. Presentation only.
 *
 * The signals API is mocked (GET only) so these assertions do not depend on
 * the e2e database; every other API call is left alone. */

const BASE = {
  analysis_id: "00000000-0000-0000-0000-00000000a001",
  symbol: "XAUUSD",
  signal_type: "buy",
  entry_price: "4114.67",
  stop_loss: "4111.70",
  take_profit: "4160.25",
  risk_reward: 15.35,
  status: "active",
  triggered_at: null,
  closed_at: null,
  profit_loss: null,
  created_at: "2026-09-28T22:09:00Z",
  confirmed_at: null,
  status_reason: null,
};

const SMC = {
  ...BASE,
  id: "00000000-0000-0000-0000-000000000400",
  timeframe: "m5",
  confidence: 0,
  strategy: "smc_ict_crt_v1",
};

const SCORED = {
  ...BASE,
  id: "00000000-0000-0000-0000-000000000052",
  timeframe: "h1",
  confidence: 52.2,
  strategy: "breakout",
};

function isApi(url: URL, path: string) {
  return url.pathname.endsWith(`/api/v1${path}`);
}

async function mockSignals(page: Page) {
  await page.route(
    (url) => isApi(url, "/signals"),
    async (route) => {
      if (route.request().method() !== "GET") return route.abort();
      await route.fulfill({ json: { items: [SMC, SCORED], page: 1, limit: 20, total: 2 } });
    },
  );
  for (const signal of [SMC, SCORED]) {
    await page.route(
      (url) => isApi(url, `/signals/${signal.id}`),
      async (route) => {
        if (route.request().method() !== "GET") return route.abort();
        await route.fulfill({ json: signal });
      },
    );
  }
}

test("the Signals list shows Rule-based — No Score for SMC, and a gauge for a scored signal", async ({
  page,
}) => {
  await mockSignals(page);
  await login(page, E2E_ADMIN);
  await page.goto("/signals");

  const badges = page.getByTestId("rule-based-confidence");
  await expect(badges).toHaveCount(1, { timeout: 15_000 });
  await expect(badges.first()).toHaveText("Rule-based — No Score");
  await expect(page.getByText("52%")).toBeVisible();
  await expect(page.getByText(/^0%$/)).toHaveCount(0);
});

test("the Signal detail page shows Rule-based — No Score instead of 0%", async ({ page }) => {
  await mockSignals(page);
  await login(page, E2E_ADMIN);
  await page.goto(`/signals/${SMC.id}`);

  await expect(page.getByTestId("signal-confidence")).toHaveText("Rule-based — No Score", {
    timeout: 15_000,
  });
});

test("a scored signal's detail page keeps its percentage", async ({ page }) => {
  await mockSignals(page);
  await login(page, E2E_ADMIN);
  await page.goto(`/signals/${SCORED.id}`);

  await expect(page.getByTestId("signal-confidence")).toHaveText("52%", { timeout: 15_000 });
});
