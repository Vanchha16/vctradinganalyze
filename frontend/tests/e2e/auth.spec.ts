import { expect, test } from "@playwright/test";

import { E2E_ADMIN, login } from "./fixtures";

/** Flow 1 (build spec §4.1): log in, land on the dashboard, reload and
 * stay logged in, log out, and confirm a protected route redirects to
 * login afterwards. */
test.describe("Auth", () => {
  test("log in lands on the dashboard", async ({ page }) => {
    await login(page, E2E_ADMIN);
    await expect(page.getByRole("link", { name: "Dashboard" }).first()).toBeVisible();
  });

  test("reloading a protected page keeps the session", async ({ page }) => {
    await login(page, E2E_ADMIN);

    await page.reload();

    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByRole("link", { name: "Dashboard" }).first()).toBeVisible();
  });

  test("logout redirects to login and protected routes redirect back", async ({ page }) => {
    await login(page, E2E_ADMIN);

    await page.getByRole("button", { name: /Account menu/ }).click();
    await page.getByRole("menuitem", { name: "Log out" }).click();

    await expect(page).toHaveURL(/\/login/);

    // A protected route must redirect an unauthenticated visitor back to
    // login rather than rendering (AuthGuard, docs/53 §3).
    await page.goto("/dashboard");
    await expect(page).toHaveURL(/\/login/);
  });
});
