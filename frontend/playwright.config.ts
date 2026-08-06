import { defineConfig, devices } from "@playwright/test";

/**
 * Phase 9C (docs/60 §7) wired into CI in Phase 9C-B - Chromium only for now,
 * cross-browser adds runtime for little value at this stage of the suite.
 *
 * Local usage is unchanged (see README.md "Running the E2E suite") -
 * developers still start both servers themselves:
 * 1. `cd backend && .venv/Scripts/python.exe scripts/seed_e2e_data.py`
 * 2. `cd backend && .venv/Scripts/python.exe scripts/run_dev.py api --e2e-db`
 *    (mock providers, dedicated `e2e.db` - never `dev.db`)
 * 3. `cd frontend && npm run dev` - reads `NEXT_PUBLIC_API_URL` from
 *    `.env.local` (defaults to `http://localhost:8000/api/v1`, matching the
 *    backend above)
 * 4. `cd frontend && npm run test:e2e`
 *
 * CI (`.github/workflows/ci.yml`'s `e2e` job) instead lets Playwright start
 * and wait for both servers itself via `webServer` below, gated on `CI` so
 * it never activates for the local flow above - a developer with their own
 * servers already running is unaffected, and `reuseExistingServer: false`
 * only applies inside the CI-only branch.
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
  // CI-only: local runs still start both servers manually (see above).
  // `/api/v1/health` is the liveness probe (no DB/Redis dependency, and
  // deliberately excluded from rate limiting) - a real readiness signal,
  // not an arbitrary sleep.
  webServer: process.env.CI
    ? [
        {
          command: "uv run python scripts/run_dev.py api --e2e-db",
          cwd: "../backend",
          url: "http://localhost:8000/api/v1/health",
          timeout: 120_000,
          reuseExistingServer: false,
        },
        {
          command: "npm run start",
          url: "http://localhost:3000",
          timeout: 120_000,
          reuseExistingServer: false,
        },
      ]
    : undefined,
});
