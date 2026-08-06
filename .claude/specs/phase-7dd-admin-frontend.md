# Build Spec — Phase 7D-D: Admin Frontend

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Depends on:** 7D-C (commit `6b7856a`) — all five endpoints are live.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.**
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Frontend only. Do NOT modify anything under `backend/`.** The API contract
   was set in 7D-C and documented in `docs/04`. If the frontend seems to need a
   backend change, **STOP and report it.**
5. **Do NOT add a charting library.** See §2 — this is a deliberate decision that
   deviates from `docs/58` §3.3's assumption, with reasoning. Do not reverse it
   on your own judgment; if you disagree, report rather than install.

---

## 1. Scope

Turn the Phase 8D placeholder pages into real pages over 7D-C's five endpoints.

| Page | Backend | Action |
|---|---|---|
| `admin/users` | `GET /admin/users` (8C) | **Done — do not touch** |
| `admin/audit-logs` | `GET /admin/logs` (8F) | **Done — do not touch** |
| `admin/system-health` | `GET /admin/system` | **Build** |
| `admin/signal-statistics` | `GET /admin/signals` + `GET /admin/analytics` | **Build** |
| `admin/api-usage` | none exists | **Leave as placeholder** |
| `admin/settings` | none exists | **Leave as-is** |
| `admin/page.tsx` (dashboard) | existing `GET /admin/users` composition | **Extend, see §5** |

Plus the two maintenance actions (§4).

Read `docs/58` §3.3 for the original description, and `docs/04`'s Admin section
for the exact response shapes (filled in by 7D-C).

---

## 2. Decision: no charting library

`docs/58` §3.3 says this phase "introduces the first chart dependency ... keep to
what `recharts` or equivalent's basic bar/line components need."

**That premise no longer holds, and you must not add one.** Here is the entire
analytics payload 7D-C actually returns (`backend/app/schemas/admin_system.py`):

```
GET /admin/analytics -> { daily_active_users: int,
                          signal_type_distribution: dict[str, int] }   # e.g. {"buy": 5, "sell": 2}
GET /admin/system    -> { database: "ok"|"down", redis: "ok"|"down",
                          signals_today: int, ai_analyses_today: int }
```

Four scalars and a dictionary with roughly two keys. `docs/58` §3.3 was written
during Phase 7D scoping and assumed `docs/25` §15's much richer analytics set
(most-viewed assets, confidence distribution, average AI response time) —
**ADR-130 deferred all of those** for lack of view-tracking and latency
infrastructure. The charts were scoped for data that does not exist.

Render these with **stat tiles and a simple proportion bar built from existing
components and CSS** — reuse `components/shared/premium`'s `Panel`/`PanelHeader`
and whatever stat-tile pattern the existing admin dashboard (`admin/page.tsx`)
already uses. `lightweight-charts` is already a dependency but is a financial
charting library; do **not** press it into service for a bar chart.

Adding a chart dependency later is easy; removing one is not. If richer
analytics ever ship, that is the moment to choose a library — with real data to
justify the choice.

**Record this in ADR-131** (§6) as an explicit narrowing of `docs/58` §3.3.

---

## 3. Pages to build

### 3.1 `admin/system-health`

Replace the `AdminComingSoon` placeholder with real data from `GET /admin/system`.

- `database` / `redis` render as clear ok/down status indicators. Reuse the
  existing `Badge` component and `lib/badge-variants` rather than inventing new
  status styling.
- `signals_today` / `ai_analyses_today` as stat tiles.
- **The endpoint returns `"down"` in a 200 response rather than erroring** — so
  a down dependency is normal data to render, not an error state. Do not treat
  it as a failed request.
- Keep the page honest about what it is: this is liveness plus counts, **not**
  telemetry (ADR-116). There is no CPU, memory, or queue-depth data. A short
  note to that effect on the page is appropriate — the existing placeholder
  pages already model this tone; match it.

### 3.2 `admin/signal-statistics`

Replace the placeholder using both `GET /admin/signals` (paginated list) and
`GET /admin/analytics`.

- `daily_active_users` as a stat tile.
- `signal_type_distribution` as a simple proportion bar or labelled counts —
  **no chart library** (§2).
- The paginated signal list as a table. **Reuse the existing admin table and
  pagination components** from `features/admin/components/` (`user-table.tsx`,
  `audit-log-table.tsx` are your models). No new primitives.

**Correct a stale comment while you are here:** that page's current docstring
says *"The existing `GET /signals` is scoped to the caller's own signals."*
**That is wrong** — 7D-C confirmed `Signal` has no `user_id` column at all and
the public endpoint never filtered by user (see ADR-130). Fix or remove the
comment; do not leave an inaccurate claim in the file.

### 3.3 Leave alone

- `admin/api-usage` — no backend exists; its placeholder correctly cites the
  `GET /metrics` gap (BACKLOG §3). **Do not fabricate numbers.**
- `admin/settings` — out of scope.
- `admin/users`, `admin/audit-logs` — already real.

---

## 4. Maintenance actions — and a safety requirement

`docs/58` §3.3: "No maintenance-action buttons beyond the two
`POST /admin/maintenance` actions actually exist to trigger."

Add exactly two: **Refresh News** and **Refresh Calendar**. Put them on the
System Health page (it is the operational page, and it already shows liveness).
If you judge Settings a better home, say so in your report and pick one — do not
put them in both.

**Safety requirements — these are not optional:**

1. **Confirm before firing.** In production these call real vendors and consume
   real quota. Reuse the existing `confirm-action-dialog.tsx` from
   `features/admin/components/` — do not build a new confirmation.
2. **The confirmation copy must say what will actually happen** — that it
   triggers a live data refresh from the configured provider and may consume
   vendor API quota. Vague "Are you sure?" text is not acceptable here.
3. **Disable the button while in flight** and show progress. The backend runs
   ingestion **synchronously** (ADR-130's recorded tradeoff), so this request can
   take many seconds. A user who double-clicks must not fire two ingestions.
4. **Handle a slow or timed-out request gracefully.** Do not leave the UI stuck
   in a permanent loading state.
5. Surface the returned counts (`articles_ingested`, or
   `events_created`/`events_updated`) on success, and the error message on
   failure, via the existing toast pattern.

---

## 5. Admin dashboard (`admin/page.tsx`)

Extend the existing dashboard with a compact system-status summary from
`GET /admin/system` — DB/Redis state and today's two counts — linking through to
System Health.

Follow the page's existing documented principle exactly: *"No fabricated
numbers: every stat here is a real, currently-derivable count."* Keep the
existing `GET /admin/users`-derived stats unchanged.

---

## 6. Supporting work

- `frontend/services/admin.ts` — extend with the five endpoints. **Do not create
  a second admin service module.**
- `frontend/services/types.ts` — response types alongside the existing `Admin*`
  types, matching `backend/app/schemas/admin_system.py` exactly.
- Hooks in `frontend/hooks/`, following `use-admin-users.ts` / `use-admin-logs.ts`.
  Mutations (the two maintenance actions) should invalidate the system-status
  query so counts refresh after a run.
- **Nav:** the Admin nav group already exists and is role-gated (8D, ADR-118).
  Every page in scope already has a nav entry. **Do not add nav items.**
- Loading / error / empty states consistent with the rest of the admin area.
- **ADR-131** in `docs/36_DECISION_RECORDS.md` after ADR-130, matching the
  neighbouring format. Must cover: the no-chart-library decision and why
  (§2), the maintenance-action confirmation requirement (§4), and that
  `api-usage` remains a placeholder pending the `/metrics` gap.
- `docs/30` mark 7D-D complete (**this completes Phase 7D**); `BACKLOG.md` §24/§26
  updated; `CHANGELOG.md` entry.

---

## 7. Verification — run these and report exact output

```
cd frontend && npm run typecheck && npm run lint && npm run build
```
All three must pass. **Do NOT run `npm run format:check`** — it fails on ~55
pre-existing files (BACKLOG §23), unrelated to your work.

**Manual check (required — there is no frontend test suite).** Backend running,
logged in as an admin. **Start the backend via `backend/scripts/run_dev.py api`**
so mock providers are in force — the maintenance buttons would otherwise call
real vendors and consume real quota (commit `9ccd471`; this exact leak happened
during 7D-C verification).

Report what you actually observed:
- System Health shows real DB/Redis status and today's counts
- Signal Statistics shows the distribution and a paginated signal list
- **Refresh News**: confirmation dialog appears with accurate copy → confirm →
  button disables during the run → success toast shows the ingested count
- The resulting audit row appears in Audit Logs
- **Refresh Calendar** likewise
- A non-admin cannot see the Admin nav or reach the pages
- `api-usage` still shows its honest placeholder

**State plainly in your report whether any external network call occurred.**

---

## 8. Done criteria

- System Health and Signal Statistics are real pages; `api-usage` untouched.
- **No new npm dependency.** `git diff frontend/package.json` shows no addition.
- Two maintenance buttons, both behind a confirmation naming the quota cost,
  both disabled in flight.
- Stale "scoped to the caller's own signals" comment corrected (§3.2).
- No backend file modified; no nav items added.
- ADR-131 written; docs/30, BACKLOG, CHANGELOG updated.
- `typecheck`/`lint`/`build` pass.
- **One commit**, `feat:` prefix, matching `git log --oneline -10` style, ending
  with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 9. Report back

What you built, exact typecheck/lint/build output, **what you actually observed
in the manual walkthrough** (not "it works"), confirmation that no npm dependency
was added, whether any external network call occurred, the commit SHA, and —
most importantly — **anything in this spec that turned out to be wrong about the
repo, or any judgment call you had to make.** If you disagree with something
here, say so rather than silently working around it. If a doc contradicts this
spec, the doc wins; stop and report the conflict.
