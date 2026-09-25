import { expect, type Page, test } from "@playwright/test";

import { E2E_ADMIN, login } from "./fixtures";

/** ADR-183. The Strategies panel used to render only the legacy
 * `disabled_strategies` rows, so `smc_enabled` - SMC-ICT-CRT-v1, a separate
 * strategy path in the same group - was returned by the API but never shown.
 *
 * The settings API is mocked so these assertions do not depend on the e2e
 * database, and every write is refused: this spec can never change a
 * setting. */

const LEGACY = [
  "trend_following", "smc", "breakout", "pullback",
  "mean_reversion", "scalping", "swing_trading", "bbma",
];

function setting(overrides: Record<string, unknown>) {
  return {
    help: "", default: null, overridden: true, minimum: null, maximum: null,
    choices: [], updated_at: null, ...overrides,
  };
}

/** Production's state on 2026-09-25: every legacy strategy off (including
 * the legacy "smc" scorer), SMC-ICT-CRT-v1 on. */
const RESPONSE = {
  propagation_seconds: 30,
  items: [
    setting({
      key: "disabled_strategies", group: "strategies", label: "Disabled strategies",
      kind: "strategies", value: LEGACY, default: [], choices: LEGACY,
    }),
    setting({
      key: "smc_enabled", group: "strategies", label: "SMC-ICT-CRT v1",
      help: "ADR-183. Its own deterministic path: H4 CRT raid, M5 MSS, FVG/OB entry.",
      kind: "bool", value: true, default: false,
    }),
    setting({
      key: "signal_ttl_hours", group: "pipeline", label: "Pending signal lifetime (hours)",
      kind: "int", value: 24, default: 24, overridden: false,
    }),
  ],
};

async function openWithMockedSettings(page: Page) {
  await page.route("**/admin/runtime-settings", async (route) => {
    if (route.request().method() !== "GET") {
      await route.abort(); // this spec must never write a setting
      return;
    }
    await route.fulfill({ json: RESPONSE });
  });
  await login(page, E2E_ADMIN);
  await page.goto("/admin/strategy-settings");
  // Same 15s bound, and the same reason, as `login()` in fixtures.ts: `next
  // dev` compiles this page on its first request, and a cold run can exceed
  // the default. Still a web-first assertion - it resolves as soon as the
  // heading renders.
  await expect(page.getByRole("heading", { name: "Strategy Settings" })).toBeVisible({
    timeout: 15_000,
  });
}

function row(page: Page, key: string) {
  return page.locator(`[data-setting="${key}"]`);
}

test("the legacy strategy rows still render, one per disabled_strategies choice", async ({ page }) => {
  await openWithMockedSettings(page);
  for (const name of LEGACY) {
    await expect(row(page, `disabled_strategies.${name}`)).toBeVisible();
  }
});

test("smc_enabled renders in the Strategies panel and shows On", async ({ page }) => {
  await openWithMockedSettings(page);
  await expect(page.getByText("Independent strategy paths")).toBeVisible();
  const smc = row(page, "smc_enabled");
  await expect(smc).toBeVisible();
  await expect(smc.getByText("SMC-ICT-CRT v1", { exact: true })).toBeVisible();
  await expect(smc.getByRole("button", { name: "On" })).toHaveAttribute("aria-pressed", "true");
  await expect(smc.getByRole("button", { name: "Off" })).toHaveAttribute("aria-pressed", "false");
});

test("the legacy SMC row stays separate and shows its own state", async ({ page }) => {
  await openWithMockedSettings(page);
  // Legacy "smc" is disabled while SMC-ICT-CRT-v1 is on: two different systems.
  const legacy = row(page, "disabled_strategies.smc");
  await expect(legacy.getByText("Smart Money Concepts (SMC)", { exact: true })).toBeVisible();
  await expect(legacy.getByRole("button", { name: "Off" })).toHaveAttribute("aria-pressed", "true");
  await expect(row(page, "smc_enabled").getByRole("button", { name: "On" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  // The legacy row does not contain the new setting, and vice versa.
  await expect(legacy.getByText("SMC-ICT-CRT v1")).toHaveCount(0);
  await expect(row(page, "smc_enabled").getByText("Smart Money Concepts (SMC)")).toHaveCount(0);
});

test("other groups still render generically", async ({ page }) => {
  await openWithMockedSettings(page);
  await expect(row(page, "signal_ttl_hours")).toBeVisible();
});
