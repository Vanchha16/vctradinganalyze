# Watchlists & Admin Architecture

> **§3 (Admin) superseded 2026-08-05 by `docs/59_ADMIN_USER_MANAGEMENT_ARCHITECTURE.md`
> (Phase 8)** - the user-management scope decided here (ADR-116) was written before a
> real user-CRUD/admin-only-provisioning requirement existed. §2 (Watchlists) is
> unaffected and remains the current plan for 7D-A/7D-B.

# 1. Scope

`docs/21_WATCHLIST_SYSTEM.md` and `docs/25_ADMIN_PANEL.md` are Phase-0 vision
documents describing far more than this project currently has schema or
infrastructure for: custom alerts, tags, pinning, AI watchlist summaries,
performance history, live CPU/disk/Redis/queue metrics, feature flags,
A/B prompt testing, "restart workers." None of that exists in this codebase
yet, and building it now would mean inventing new architecture rather than
implementing documented architecture.

This phase (7D) narrows both to exactly what `docs/03_DATABASE_DESIGN.md`
and `docs/04_API_SPECIFICATION.md` already commit to concretely:

- **Watchlists**: a named list per user, with asset membership. Nothing else.
- **Admin**: the 7 endpoints docs/04 §Admin actually lists, gated by a new
  RBAC-enforcement dependency that has never existed in this project before.

Sub-phases:

- **7D-A** Watchlists Backend
- **7D-B** Watchlists Frontend
- **7D-C** Admin Backend (RBAC enforcement + the 7 documented endpoints)
- **7D-D** Admin Frontend

Explicitly out of scope for this phase (real docs/21/25 vision, deferred, not
forgotten): custom alerts, tags, pinning, AI watchlist summary, performance
history, unlimited-vs-10-pinned premium gating (docs/21 §7-16, ADR-114);
system/queue/Redis/CPU monitoring, feature flags, maintenance tools beyond
what `POST /admin/maintenance` concretely does today, A/B prompt testing
(docs/25 §11-17, ADR-116); granular `roles`/`permissions`/`role_permissions`
tables (docs/23 §14, still deferred per BACKLOG.md §2 - this phase reuses the
existing simple `UserRole` enum, ADR-115); session/device-management UI and
Subscription (still "7D+" beyond this scoping, unstarted).

---

# 2. Watchlists (7D-A/7D-B)

## 2.1 Persistence Model

Exactly `docs/03` §12's fields, no additions:

`watchlists` (`UUIDMixin` + `CreatedAtMixin`, append-only creation record,
name is the only mutable field so no `updated_at` is needed):

| Field | Notes |
|---|---|
| `id` | generated |
| `user_id` | FK to `users`, `ON DELETE CASCADE` |
| `name` | `String(255)`, not unique - a user may have two watchlists named the same, no doc requires otherwise |
| `created_at` | |

`watchlist_items` (`UUIDMixin` + `CreatedAtMixin`):

| Field | Notes |
|---|---|
| `id` | generated |
| `watchlist_id` | FK to `watchlists`, `ON DELETE CASCADE` |
| `asset_id` | FK to `assets`, `ON DELETE CASCADE` |
| `created_at` | |

Unique constraint on `(watchlist_id, asset_id)` — an asset can't be added to
the same watchlist twice. Same inferred-uniqueness precedent as
`OAuthAccount`'s `(provider, provider_user_id)` (ADR-022) and
`signal_bookmarks`' equivalent (ADR-090).

## 2.2 Service & Repository

`WatchlistRepository`/`WatchlistService` follow the existing
repository/service split (e.g. `SignalRepository`/`SignalEngine`'s
persistence half). All operations scoped to `user_id` — a user can only see
and mutate their own watchlists; no sharing, no admin override in this phase.

## 2.3 API (docs/04 §Watchlists, unchanged from the existing spec)

```
GET    /watchlists                      list the caller's watchlists (with item counts)
POST   /watchlists                      create {name}
PUT    /watchlists/{id}                 rename {name}
DELETE /watchlists/{id}                 delete (cascades items)
POST   /watchlists/{id}/assets          add {asset_id}
DELETE /watchlists/{id}/assets/{asset}  remove
```

`GET /watchlists/{id}` (single watchlist with resolved asset rows) is an
inferred addition beyond docs/04's literal list — needed for the frontend
detail view, same category of inference as `signals.created_at` (ADR-091).

## 2.4 Frontend (7D-B)

Replaces the `EmptyState`-only placeholder (ADR-103) with real CRUD, reusing
Phase 7B/7C's established patterns — no new UI primitives needed:

- `features/watchlists/` — `WatchlistCard` (name, item count, quick-delete),
  `WatchlistDetail` (asset table reusing Markets' `AssetTable` columns:
  symbol, price, daily change — no watchlist-specific columns like
  confidence/trade-quality/risk, since docs/21 §5's richer per-asset display
  isn't backed by any single existing endpoint and composing one client-side
  per row would mean N+1 calls to `/analysis/*` for every watchlist view)
- `services/watchlists.ts` + one TanStack Query hook per operation, same
  shape as every other Phase 7B service module
- `app/(protected)/watchlists/page.tsx` — list + create dialog
- `app/(protected)/watchlists/[id]/page.tsx` — detail + add/remove assets
  (asset picker reuses `SymbolTimeframePicker`'s asset-search half)

---

# 3. Admin (7D-C/7D-D)

## 3.1 RBAC Enforcement Dependency (new, blocks everything else here)

No permission-checking dependency has ever existed in this project —
`get_current_user` (Phase 2C) intentionally only authenticates (BACKLOG.md
§4/§20). This phase adds the first one, scoped to exactly what it needs:

`require_role(*roles: UserRole)` — a FastAPI dependency factory, `app/
dependencies/rbac.py`, wrapping `get_current_user` and raising `403` if
`current_user.role not in roles`. No granular permission strings
(`admin.dashboard`, `signals.publish` — docs/23 §14) — those require the
`roles`/`permissions`/`role_permissions` tables docs/23 §12-14 describes,
which remain explicitly deferred (BACKLOG.md §2, unchanged by this phase,
ADR-115). Every `/admin/*` route requires `UserRole.ADMIN` or
`UserRole.SUPER_ADMIN`; docs/23 §13's Moderator/Support tiers get no routes
in this phase since none of the 7 documented endpoints map to their listed
permissions ("Manage Reports," "Assist Users").

## 3.2 API (docs/04 §Admin, unchanged from the existing spec)

```
GET  /admin/users        paginated user list + search (email/role filter)
GET  /admin/signals      paginated signal list, admin view (all users, not just caller's)
GET  /admin/system       liveness of DB/Redis (reuses the existing /health/ready checks,
                          not new infrastructure - see ADR-116) + today's counts
                          (signals generated, AI analyses run - simple COUNT queries)
GET  /admin/logs         paginated AuditLog read, existing table, existing rows since Phase 2B
GET  /admin/analytics    daily active users (distinct UserSession.user_id today),
                          recommendation distribution (GROUP BY on signals.recommendation)
POST /admin/news         manual news refresh - calls the existing NewsIngestionPipeline
                          directly (already built, Phase 5A), same trigger as the Celery
                          beat schedule, just admin-invoked
POST /admin/maintenance  scoped to {"action": "refresh_news" | "refresh_calendar"} only -
                          both call existing ingestion pipelines directly (ADR-117).
                          No "restart workers"/"clear cache"/"rebuild indicators" - none of
                          docs/25 §17's other actions have a concrete implementation to call
```

`GET /admin/system`'s "Database Status/Redis Status/Queue Status/API Status"
(docs/25 §3) is **not** live CPU/memory/queue-depth telemetry — no metrics
collection exists anywhere in this project. It reuses the existing
`/health`/`/health/ready` liveness checks (Phase 1) plus simple `COUNT`
queries, per ADR-116. Genuine system observability (Prometheus `/metrics`,
Celery queue inspection) is tracked separately in BACKLOG.md §3 and is a
prerequisite for ever building docs/25's real monitoring dashboard.

## 3.3 Frontend (7D-D)

- Role-gated `Admin` nav item in `Sidebar` (considered and deliberately
  dropped in 7A pending a real destination — now has one, ADR-118), rendered
  only when `useAuth().user.role` is `admin`/`super_admin`
- `app/(protected)/admin/` — `users` (searchable table), `signals` (admin
  view, all users), `system` (liveness + today's counts), `logs` (AuditLog
  table with filters), `analytics` (simple charts, reusing whatever chart
  library choice Phase 7C already settled if any — none was added, so this
  introduces the first chart dependency; keep to what `recharts` or
  equivalent's basic bar/line components need, no new design work)
- No maintenance-action buttons beyond the two `POST /admin/maintenance`
  actions actually exist to trigger (refresh news, refresh calendar)

---

# 4. Testing Strategy

Same as every prior backend/frontend phase: backend RBAC dependency, service,
and repository logic covered by dedicated tests (every role/permission
branch, every admin endpoint's success/403/404 paths); frontend verified via
`npm run typecheck`/`lint`/`build` plus a manual browser-driven walkthrough
(create/rename/delete watchlist, add/remove assets; log in as an admin user,
confirm the Admin nav item appears and each page loads; log in as a
non-admin user, confirm `/admin/*` routes redirect/403 and the nav item is
hidden). Coverage tooling remains not installed (BACKLOG.md §4), verified by
inspection as in every prior phase.

---

# 5. Out of Scope for Phase 7D

Custom alerts, tags, pinning, AI watchlist summary/performance history
(docs/21 §6-16, ADR-114); granular permission tables (docs/23 §12-14,
ADR-115); live system/queue/Redis/CPU metrics, feature flags, "restart
workers"/"clear cache"/"rebuild indicators," A/B prompt testing (docs/25
§11-17, ADR-116/ADR-117); Moderator/Support role routes (no documented
endpoint maps to their permissions yet); session/device-management UI
(BACKLOG.md §4/§6/§20, still blocked on its own API-route decision);
Subscription/Billing (docs/24, untouched); any change to the existing
`UserRole` enum's values.
