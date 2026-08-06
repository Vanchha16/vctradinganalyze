import { expect, test } from "@playwright/test";

import { E2E_ADMIN, login } from "./fixtures";

/** Flow 6 / regression guard (build spec §4.6): walks Dashboard -> Markets
 * -> an asset detail -> Watchlists -> an Admin page and asserts no request
 * returns 429 and no CORS error appears in the console. Directly protects
 * 9A's riskiest failure mode - per-IP limits set below real usage
 * (ADR-132) - previously guarded only by a one-off manual check. */
test("normal navigation across pages triggers no rate limiting or CORS errors", async ({ page }) => {
  const rateLimited: string[] = [];
  const corsErrors: string[] = [];

  page.on("response", (response) => {
    if (response.status() === 429) rateLimited.push(response.url());
  });
  page.on("console", (message) => {
    if (message.type() === "error" && /CORS/i.test(message.text())) {
      corsErrors.push(message.text());
    }
  });

  await login(page, E2E_ADMIN);

  await page.goto("/markets");
  await expect(page.getByRole("heading", { name: "Markets" })).toBeVisible();

  const firstAssetLink = page.getByRole("link", { name: "EURUSD" }).first();
  await firstAssetLink.click();
  await expect(page).toHaveURL(/\/markets\/EURUSD/);

  await page.goto("/watchlists");
  await expect(page.getByRole("heading", { name: "Watchlists" })).toBeVisible();

  await page.goto("/admin");
  await expect(page).toHaveURL(/\/admin$/);

  expect(rateLimited, `429 responses: ${rateLimited.join(", ")}`).toHaveLength(0);
  expect(corsErrors, `CORS console errors: ${corsErrors.join(", ")}`).toHaveLength(0);
});
