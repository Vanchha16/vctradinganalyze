import { expect, test } from "@playwright/test";

import { E2E_ADMIN, E2E_NON_ADMIN, login } from "./fixtures";

/** Flow 3 (build spec §4.3, Phase 8C/8D): list loads, search/filter
 * narrows, Add/Edit dialogs open. Deliberately does not exercise
 * destructive actions (delete, role change, disable) against the seeded
 * admin the whole suite depends on - the Edit dialog is opened against
 * the seeded non-admin instead, and closed without submitting, so no
 * other test's state is mutated. */
test.describe("Admin user management", () => {
  test("user list loads and search narrows it", async ({ page }) => {
    await login(page, E2E_ADMIN);
    await page.goto("/admin/users");

    // UserTable (desktop) and UserCardList (mobile) both render at once,
    // CSS-toggled by breakpoint - scope to the desktop table to avoid a
    // strict-mode duplicate-match, same email text appears in both.
    const table = page.getByRole("table");

    await expect(page.getByRole("heading", { name: "Users", exact: true })).toBeVisible();
    await expect(table.getByText(E2E_NON_ADMIN.email)).toBeVisible();

    await page.getByPlaceholder("Email, username, or name…").fill("nonexistent-search-term-xyz");
    await expect(page.getByText(E2E_NON_ADMIN.email)).toHaveCount(0);
    await expect(page.getByText("No users found")).toBeVisible();

    await page.getByPlaceholder("Email, username, or name…").fill("e2e_user");
    await expect(table.getByText(E2E_NON_ADMIN.email)).toBeVisible();
  });

  test("Add user dialog opens", async ({ page }) => {
    await login(page, E2E_ADMIN);
    await page.goto("/admin/users");

    await page.getByRole("button", { name: "Add user" }).click();
    await expect(page.getByRole("dialog").getByText("Add user")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("Edit user dialog opens for the non-admin target", async ({ page }) => {
    await login(page, E2E_ADMIN);
    await page.goto("/admin/users");

    await page
      .getByRole("row", { name: new RegExp(E2E_NON_ADMIN.email) })
      .getByRole("button", { name: /^Actions for/ })
      .click();
    await page.getByRole("menuitem", { name: "Edit" }).click();

    await expect(page.getByRole("dialog").getByText("Edit user")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });
});
