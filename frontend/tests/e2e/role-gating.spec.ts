import { expect, test } from "@playwright/test";

import { E2E_NON_ADMIN, login } from "./fixtures";

/** Flow 5 (build spec §4.5): the seeded non-admin sees no Admin nav entry
 * and is redirected away from an /admin/* URL (AdminGuard, docs/59 §5.1). */
test("non-admin has no Admin nav entry and is redirected away from /admin/*", async ({ page }) => {
  await login(page, E2E_NON_ADMIN);

  await expect(page.getByRole("link", { name: "Admin Dashboard" })).toHaveCount(0);
  await expect(page.getByText("Admin", { exact: true })).toHaveCount(0);

  await page.goto("/admin/users");
  await expect(page).toHaveURL(/\/dashboard/);
});
