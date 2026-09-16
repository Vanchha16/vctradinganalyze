# Build Spec — Signal Performance Metrics (ADR-174)

**Status:** Approved, ready to build. Written by the planning session 2026-09-16.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Most relevant here:
   never violate an accepted ADR; documentation is the source of truth; never
   invent architecture; prefer improving existing files over creating new ones.
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **No new table. No migration. Nothing is written to the database.** This phase
   is read-only end to end. If you believe a column or table is needed, **STOP and
   report it** — do not add one. ADR-174 rejected a rollup table explicitly.
5. **Read `docs/36_DECISION_RECORDS.md` § ADR-174 in full before starting.** This
   spec implements it and may not contradict it.
6. **No caching.** No `functools.cache`, no Redis, no precomputation. Every other
   engine in this project recomputes on each call; a stale win rate is worse than
   a slow one.

---

## 1. Critical context — four traps that will produce wrong numbers

This phase is arithmetic over a table you already have. The risk is not that it
fails to run; it is that it runs and reports **plausible, wrong numbers**. All
four traps below have already bitten this project once.

### 1.1 Pre-ADR-137 rows corrupt every rate

55 BUY signals created `2026-08-05` to `2026-08-07` predate ADR-137's TRIGGERED
gate, when stop loss and take profit were evaluated before price ever reached
entry. **34 of them are stored `SUCCESSFUL`/`STOPPED_OUT` with `triggered_at IS
NULL`** — a state current code cannot produce.

Included silently they make BUY look like it fills at **14%**. The true post-fix
rate is **56%**. Verify both numbers yourself before you start, so you recognise
a wrong result when you see one.

**Every query in this phase filters `created_at >= settings.signal_metrics_epoch`.**

### 1.2 Open/expired status is computed, not stored

`app/services/signal/status_resolver.py::effective_status` is read-time only
(ADR-088). An `ACTIVE` row past `signal_ttl_hours` is really `EXPIRED`; a
`TRIGGERED` row past `signal_triggered_ttl_hours` is really `CLOSED` with null
`profit_loss`.

- **Win/loss counts:** read the stored status directly. `SUCCESSFUL` and
  `STOPPED_OUT` are terminal and pass through `effective_status` unchanged, so
  this is safe **and** must be paired with `triggered_at IS NOT NULL`.
- **Open/expired counts:** you MUST resolve through `effective_status`. Reading
  the stored column here is the exact bug already recorded in `BACKLOG.md`, where
  an unfilled signal past its TTL showed under "active" and never under "expired".

### 1.3 `profit_loss` is price points, not money

`app/services/signal_monitoring_service.py` sets it to
`closed_price - entry_price` (inverted for a SELL). Summing it assumes every
trade carried the same size and every instrument the same tick value — true
today with one asset and one fixed EA lot, false the moment either changes.

**The field is named `total_points`. Never `total_pnl`, never `profit_usd`.** The
response carries a note stating the assumption. Do not "improve" this naming.

### 1.4 A rate without its denominator is not a result

28 filled trades exist today, so most breakdowns will have single-digit `n`. A
win rate over 3 trades and one over 300 render identically unless you force the
difference. **Every metric object carries its own `trades` count**, and the UI
labels anything under 30 as not yet meaningful.

---

## 2. Read before writing

- `docs/36_DECISION_RECORDS.md` → ADR-174 (this phase), ADR-088 (read-time
  status), ADR-137 (the TRIGGERED gate), ADR-167 (risk review, shadow mode),
  ADR-168 (replacement)
- `BACKLOG.md` §44 — the fill-rate baseline and the trap in §1.1
- `app/models/signal.py`, `app/services/signal/status_resolver.py`
- `app/repositories/signal_repository.py`
- `app/services/admin_system_service.py` — the service shape to mirror
- `app/api/v1/routes/admin_logs.py` — the route shape to mirror
- `app/schemas/admin_system.py` — the schema shape to mirror

---

## 3. Backend deliverables

### 3.1 Setting — `app/config/settings.py`

Add alongside the other signal settings:

```python
#: Signals created before this are excluded from every performance metric
#: (ADR-174). They predate ADR-137's TRIGGERED gate and carry outcomes that
#: current code cannot produce. Advance this after any future fix that
#: invalidates earlier outcomes.
signal_metrics_epoch: datetime = datetime(2026, 8, 8, tzinfo=UTC)
```

A setting, not a constant — a hardcoded date buried in SQL is how the wrong
number gets shipped.

### 3.2 `SignalRepository` — add aggregate query methods

Extend the existing repository; do not create a second one. Every method takes
`epoch: datetime` and filters `created_at >= epoch`.

Aggregate **in SQL**, not by loading rows into Python — except where
`effective_status` is required (§1.2), which needs the rows.

Suggested methods (adjust names to match the file's conventions):

- `performance_totals(epoch)` — trades filled, wins, losses, sum/avg of
  `profit_loss` for wins and for losses separately
- `performance_by(epoch, dimension)` — the same, grouped by `strategy`,
  `timeframe` or `signal_type`
- `performance_by_confidence(epoch, bands)` — the same, grouped into confidence
  bands
- `fill_counts(epoch)` — signals created vs signals with `triggered_at IS NOT
  NULL`, overall and by `signal_type`
- `risk_review_outcomes(epoch)` — filled-trade outcomes split by the ADR-167
  review verdict on the joined `ai_analysis` row (approve / veto / none)
- `replacement_outcomes(epoch)` — outcomes of signals whose `status_reason`
  records an ADR-168 replacement, against the rest

Read `app/models/ai_analysis.py` for the actual risk-review column names. **If
the verdict is not queryable from `ai_analysis`, STOP and report it** rather
than inventing a column.

### 3.3 `SignalPerformanceService` (new) — `app/services/signal_performance_service.py`

Mirrors `AdminSystemService`'s shape. Owns the arithmetic the repository should
not: win rate, expectancy, profit factor, and the open/expired counts that need
`effective_status`.

Definitions — implement exactly these:

| Metric | Definition |
|---|---|
| `trades` | filled only: `triggered_at IS NOT NULL` |
| `wins` / `losses` | stored `SUCCESSFUL` / `STOPPED_OUT` |
| `win_rate` | `wins / (wins + losses)`, `None` when the denominator is 0 |
| `total_points` | `sum(profit_loss)` |
| `avg_win` / `avg_loss` | mean `profit_loss` of wins / of losses |
| `expectancy` | `total_points / trades`, `None` when `trades` is 0 |
| `profit_factor` | `sum(wins) / abs(sum(losses))`, `None` when losses sum to 0 |
| `fill_rate` | `filled / created`, `None` when `created` is 0 |

**Return `None`, never `0`, for an undefined ratio.** A 0% win rate and "no
trades yet" are different facts and the UI must be able to tell them apart.

Use `Decimal` throughout — `profit_loss` is `Numeric(20, 8)`. Do not round in
the service; let the schema do it.

Also expose `CLOSED` (TTL-expired live trades) as its own count via
`effective_status`. Those are real filled trades that reached neither target and
have null `profit_loss`; they must not be silently dropped from `trades`, nor
counted as wins or losses. **State their count explicitly in the response** so
the reader can see that `wins + losses` may be less than `trades`.

### 3.4 Schemas — `app/schemas/admin_performance.py` (new)

A reusable `PerformanceMetrics` block (the table above, every field optional
except `trades`), plus a top-level response carrying:

- `epoch` — the `signal_metrics_epoch` actually used
- `points_note` — a fixed string stating that P&L is price points, assumes one
  symbol and one lot size, and is not currency
- `overall`, `by_strategy`, `by_timeframe`, `by_signal_type`, `by_confidence`
- `risk_review` (ADR-167 comparison) and `replacements` (ADR-168 comparison)

`epoch` and `points_note` are **required**. A caller must never be able to read a
rate without knowing what it excludes or what units it is in.

### 3.5 Route — `GET /admin/performance`

New module `app/api/v1/routes/admin_performance.py`, registered in
`app/api/v1/router.py` beside the other admin routes. `require_admin`-gated, same
as `admin_logs`. **GET only** — no other method may exist on this path.

Do not extend `GET /admin/analytics`. ADR-174 rejected that: it answers "who is
using this", this answers "does it work".

### 3.6 Tests — `backend/tests/test_admin_performance_api.py`

Cover at minimum:

1. **The §1.1 trap:** seed a pre-epoch signal with `triggered_at IS NULL` and a
   stored `SUCCESSFUL`, assert it is excluded from every count.
2. **The §1.2 trap:** an `ACTIVE` signal past `signal_ttl_hours` counts as
   expired, not open; a `TRIGGERED` signal past `signal_triggered_ttl_hours`
   counts as `CLOSED`, is excluded from wins and losses, and does not break
   `trades`.
3. Each metric against a hand-computed fixture — including the `None` cases for
   every ratio with a zero denominator.
4. `profit_factor` when losses sum to zero.
5. Every breakdown returns its own `trades` count.
6. `epoch` and `points_note` are always present.
7. 403 for a non-admin, 401 unauthenticated.
8. The OpenAPI schema exposes no non-GET method under `/admin/performance`.

Follow `tests/test_admin_logs_api.py` for fixtures and auth helpers.

---

## 4. Frontend deliverable

New page at `frontend/app/(protected)/admin/performance/page.tsx`, following
`admin/audit-logs` exactly for structure, loading and error states.

- Extend `services/admin.ts` with `getAdminPerformance` — **no second admin
  service module**
- Add the response types alongside the existing `Admin*` types
- New hook `use-admin-performance.ts`, mirroring `use-admin-logs.ts`
- Reuse `StatCard`, `Panel`, `Table`, `Badge`, `EmptyState`, `ErrorCard` —
  **add no new UI primitive and no chart library** (ADR-131 still stands)

Required on the page:

- Headline tiles: trades, win rate, expectancy, profit factor, total points
- One table per breakdown, each row showing **its own `trades` count**
- Rows with `trades < 30` visibly marked as not yet meaningful — a `Badge`, or
  muted text. Do not hide them.
- The `points_note` string rendered verbatim near the total, not buried
- The `epoch` shown, so the reader knows the window
- `None` ratios rendered as `—`, never as `0%`

Link it from `admin/page.tsx` the way the other admin pages are linked.

---

## 5. Verification — run these and report exact output

```bash
cd backend
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check . --output-format=concise
.venv/Scripts/python.exe -m mypy app
cd ../frontend
npm run typecheck && npm run lint && npm run build
```

Then, against a local backend with seeded data, confirm by hand:

- A pre-epoch signal is absent from every figure
- A ratio with a zero denominator renders `—`, not `0%`
- A breakdown row under 30 trades is marked

**Do not verify against production.** Read-only or not, it is not a test fixture.

---

## 6. Done criteria

- [ ] `GET /admin/performance` returns every metric in §3.3, admin-gated
- [ ] `epoch` and `points_note` present in every response
- [ ] No migration, no new table, no write path, no caching
- [ ] Pre-epoch rows excluded; `effective_status` used for open/expired
- [ ] `CLOSED` trades counted and stated separately
- [ ] Admin page renders all breakdowns with denominators and small-sample marks
- [ ] Backend test count increased by the new tests, none failing
- [ ] `ruff`, `mypy`, frontend `typecheck`/`lint`/`build` all clean

---

## 7. Report back

State plainly:

1. Each verification command and its **exact** output — not a summary
2. The real numbers the endpoint returned against your seeded data
3. Anything in this spec that turned out to be wrong about the codebase — name
   it rather than working around it silently
4. Anything you chose not to do, and why

If the ADR-167 risk-review verdict is not queryable from `ai_analysis` (§3.2),
say so and leave that one comparison unbuilt. **Do not invent a column, and do
not guess at a verdict from the narration text.**
