import { expect, test } from "@playwright/test";

import { E2E_NON_ADMIN, login } from "./fixtures";

/** Flow 2 (build spec §4.2, Phase 7D-B): empty state -> create -> appears
 * with count 0 -> open detail -> add an asset -> count updates -> remove
 * -> rename -> delete. One sequential test rather than several
 * independent ones - it is inherently a single lifecycle, and ending in
 * delete means re-running leaves no leftover state (§5's determinism
 * requirement). Uses the non-admin account since watchlists are a
 * per-user feature with no admin-specific behaviour to cover. */
test("watchlist create, add/remove asset, rename, delete", async ({ page }) => {
  const name = `E2E Watchlist ${Date.now()}`;
  const renamedName = `${name} (renamed)`;

  await login(page, E2E_NON_ADMIN);
  await page.goto("/watchlists");

  // Create - both the PageHeader action and (while the list is empty) the
  // EmptyState action render a "New watchlist" button; `.first()` picks
  // either, they're equivalent.
  await page.getByRole("button", { name: "New watchlist" }).first().click();
  await page.getByLabel("Name", { exact: true }).fill(name);
  await page.getByRole("button", { name: "Create" }).click();

  await expect(page.getByText(name)).toBeVisible();
  await expect(page.getByText("0 assets")).toBeVisible();

  // Open detail
  await page.getByRole("link", { name: "Open" }).first().click();
  await expect(page).toHaveURL(/\/watchlists\/[^/]+$/);
  await expect(page.getByRole("heading", { name })).toBeVisible();

  // Add an asset - both the PageHeader action and (while empty) the
  // AssetTable/EmptyState action render "Add asset"; `.first()` picks
  // either, they're equivalent.
  await page.getByRole("button", { name: "Add asset" }).first().click();
  await page.getByRole("combobox").click();
  await page.getByRole("option").first().click();
  await page.getByRole("button", { name: "Add", exact: true }).click();
  await expect(page.getByText("1 asset")).toBeVisible();

  // Remove it
  const removeButton = page.getByRole("button", { name: /^Remove / });
  await removeButton.click();
  await expect(page.getByText("0 assets")).toBeVisible();

  // Rename
  await page.getByRole("button", { name: "Rename" }).click();
  await page.getByLabel("Name", { exact: true }).fill(renamedName);
  await page.getByRole("button", { name: "Save" }).click();
  await expect(page.getByRole("heading", { name: renamedName })).toBeVisible();

  // Delete
  await page.getByRole("button", { name: "Delete", exact: true }).click();
  await page.getByRole("alertdialog").getByRole("button", { name: "Delete" }).click();
  await expect(page).toHaveURL(/\/watchlists$/);
  await expect(page.getByText(renamedName)).toHaveCount(0);
});
