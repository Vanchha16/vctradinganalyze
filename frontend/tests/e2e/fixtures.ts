import { expect, type Page } from "@playwright/test";

/**
 * Shared E2E credentials/helpers (Phase 9C, docs/60 §7). Match the
 * accounts `backend/scripts/seed_e2e_data.py` creates - never register a
 * user here, since public registration is closed (`allow_public_
 * registration=False`) and re-seeding is how a known state is restored,
 * not creating accounts through the UI.
 */
export const E2E_ADMIN = {
  email: "e2e-admin@example.invalid",
  password: "E2E-Test-Password9",
};

export const E2E_NON_ADMIN = {
  email: "e2e-user@example.invalid",
  password: "E2E-Test-Password9",
};

/** Logs in via the real login form and waits for the dashboard to load -
 * every flow test needs this as setup, so it lives here once rather than
 * being copy-pasted per spec file.
 *
 * The generous 15s timeout (vs. Playwright's 5s default) is not an
 * arbitrary wait - it's a longer bound on the same web-first assertion,
 * needed because `next dev` compiles /login and /dashboard on first
 * request; a cold suite run can otherwise exceed the default before the
 * dev server finishes compiling. It still resolves as soon as the URL
 * actually changes, no sleep involved. */
export async function login(page: Page, credentials: { email: string; password: string }) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(credentials.email);
  await page.getByLabel("Password", { exact: true }).fill(credentials.password);
  await page.getByRole("button", { name: "Sign in" }).click();
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 15_000 });
}
