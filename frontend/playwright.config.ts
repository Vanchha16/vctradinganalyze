import { defineConfig, devices } from "@playwright/test";

/**
 * Phase 9C (docs/60 §7) - local-first E2E only, no CI wiring yet (see
 * BACKLOG.md/docs/60 for why). Chromium only for now - cross-browser adds
 * runtime for little value at this stage of the suite.
 *
 * Expected local setup (see README.md "Running the E2E suite"):
 * 1. `cd backend && .venv/Scripts/python.exe scripts/seed_e2e_data.py`
 * 2. `cd backend && .venv/Scripts/python.exe scripts/run_dev.py api --e2e-db`
 *    (mock providers, dedicated `e2e.db` - never `dev.db`)
 * 3. `cd frontend && npm run dev` - reads `NEXT_PUBLIC_API_URL` from
 *    `.env.local` (defaults to `http://localhost:8000/api/v1`, matching the
 *    backend above)
 * 4. `cd frontend && npm run test:e2e`
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  workers: 1,
  // Raised from Playwright's 5s default - not an arbitrary wait, still a
  // web-first assertion that resolves the moment its condition is true,
  // but `next dev` compiles each route on its first request, which can
  // exceed 5s on a cold suite run. Fine locally; revisit once/if this
  // suite runs against a production build in CI (§7's deferred next step).
  expect: { timeout: 10_000 },
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
