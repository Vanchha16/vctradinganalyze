import { expect, test } from "@playwright/test";

import { E2E_ADMIN, login } from "./fixtures";

/** Flow 4 (build spec §4.4, Phase 7D-C): Refresh News shows its
 * confirmation dialog with the quota warning, confirming succeeds, and an
 * audit row appears in Audit Logs. Mock providers (backend started via
 * `run_dev.py api --e2e-db`, which forces `MARKET_DATA_PROVIDERS`/`NEWS_
 * PROVIDERS`/etc. to `["mock"]`) make this safe and fast - no real vendor
 * is ever called. */
test("Refresh News shows confirmation, succeeds, and is audited", async ({ page }) => {
  await login(page, E2E_ADMIN);
  await page.goto("/admin/system-health");

  await page.getByRole("button", { name: "Refresh News" }).click();

  const dialog = page.getByRole("alertdialog");
  await expect(dialog.getByText("Refresh news now?")).toBeVisible();
  await expect(dialog.getByText(/vendor API quota/)).toBeVisible();

  await dialog.getByRole("button", { name: "Refresh News" }).click();
  await expect(page.getByText(/News refreshed/)).toBeVisible();

  await page.goto("/admin/audit-logs");
  await expect(page.getByText(/admin news refreshed/i).first()).toBeVisible();
});
