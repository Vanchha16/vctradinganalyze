# Build Spec — Phase 7D-B: Watchlists Frontend

**Status:** Approved, ready to build. Written by the planning session 2026-08-06.
**Depends on:** 7D-A (backend), completed in commit `b100ac2`. The API is live.
**Executor:** builder / CLI session. Read this file in full before writing any code.

---

## 0. Hard constraints

1. **Never read, write, or run anything outside `E:\VideCode\ClaudeTrading_ChatGPT`.**
2. **Read `CLAUDE.md` at the repo root first and obey it.** Most relevant here:
   never violate an accepted ADR; documentation is the source of truth; never
   invent architecture; prefer improving existing files over creating new ones.
3. **You may commit. Do NOT push. Do NOT amend existing commits.** Work on `main`.
4. **Frontend only. Do NOT modify anything under `backend/`.** The API contract
   was set in 7D-A and is documented in `docs/04` and `docs/58` §2.3. If the
   frontend seems to need a backend change, **STOP and report it** — do not
   change the backend to suit the client. (See §4 landmine 1, which is exactly
   this trap.)

---

## 1. Read these first

- `docs/58_WATCHLISTS_ADMIN_ARCHITECTURE.md` **§2.4** — the authoritative spec
  for this phase. Short; follow it literally.
- `docs/36_DECISION_RECORDS.md` — **ADR-114** (Watchlists scope), **ADR-103**
  (the placeholder this replaces), **ADR-128** (7D-A's API decisions).
- `backend/app/schemas/watchlist.py` — the exact response shapes you must type
  against. Reproduced in §2.1 below, but verify against the file.

**Explicitly out of scope** (ADR-114 — deliberately excluded, not forgotten;
building any of them violates the ADR): custom alerts, tags, pinning, AI
watchlist summaries, performance history, sharing.

**Also explicitly excluded by docs/58 §2.4:** any per-asset analysis column
(confidence, trade quality, risk). Those aren't backed by a single endpoint,
and composing them client-side would mean N+1 calls to `/analysis/*` for every
watchlist view. The asset table shows **symbol, price, daily change only** —
the same columns Markets' `AssetTable` already renders.

---

## 2. The API you are building against (already live)

```
GET    /watchlists                          -> { items: WatchlistSummary[] }
GET    /watchlists/{id}                     -> WatchlistDetail
POST   /watchlists            {name}        -> WatchlistSummary
PUT    /watchlists/{id}       {name}        -> WatchlistSummary
DELETE /watchlists/{id}                     -> 204
POST   /watchlists/{id}/assets  {asset_id}  -> add
DELETE /watchlists/{id}/assets/{asset_id}   -> remove
```

### 2.1 Response shapes

`WatchlistSummary`: `id`, `name`, `item_count`, `created_at`
`WatchlistDetail`: `id`, `name`, `created_at`, `assets: AssetResponse[]`

Note the asymmetry, it is deliberate: the **list** endpoint returns counts only,
the **detail** endpoint returns resolved asset rows. Don't fetch detail for
every card to show a count — `item_count` is already there.

### 2.2 Error behaviour you must handle

- Another user's watchlist id returns **404**, not 403 (deliberate — ids must
  not be probeable). Treat 404 as "not found" in the UI; do not special-case it.
- Adding an asset already in the watchlist returns a **conflict**. Surface it as
  a friendly message, not a crash.
- Adding an unknown `asset_id` returns **404**.

---

## 3. Deliverables

### 3.1 `frontend/services/watchlists.ts` (new)

Thin wrappers over the seven endpoints. **Mirror `frontend/services/admin.ts`
exactly** — same import style from `@/services/api-client`, same
module docstring convention referencing the doc section, no business logic.

Add the response/request types to `frontend/services/types.ts` alongside the
existing `Admin*` types, matching §2.1.

### 3.2 `frontend/services/api-client.ts` — add `apiPut`

**There is currently no `apiPut`.** Only `apiGet`, `apiPost`, `apiPatch`,
`apiDelete` exist. The rename endpoint is `PUT`, so add `apiPut` following the
existing `apiPatch` implementation exactly (`apiPatch` was itself added this
way during Phase 8D — same additive precedent). See §4 landmine 1.

### 3.3 Hooks — `frontend/hooks/`

One hook per operation, following the existing naming and structure. Read
`use-admin-users.ts` and `use-admin-user-actions.ts` first — that pair is the
closest analogue (a list hook plus a mutations hook) and you should mirror the
split rather than inventing a new arrangement.

Suggested: `use-watchlists.ts` (list), `use-watchlist.ts` (detail),
`use-watchlist-actions.ts` (create/rename/delete/add/remove mutations).

Mutations must invalidate the relevant TanStack Query keys so the list and
detail views stay consistent after a change — follow how the admin actions hook
does its invalidation.

### 3.4 `frontend/features/watchlists/components/` (new)

- **`WatchlistCard`** — name, item count, quick-delete. Links to the detail page.
- **`WatchlistDetail`** — the asset table. **Reuse Markets' `AssetTable`**
  (`frontend/features/markets/components/asset-table.tsx`) rather than writing a
  new table; read it first and check whether it can be reused directly or needs
  a small additive prop (e.g. a per-row action slot for "remove"). If it needs a
  change, keep that change purely additive so Markets is unaffected.
- Dialogs for create and rename, and a delete confirmation. **Reuse the existing
  primitives** — `features/admin/components/confirm-action-dialog.tsx` and the
  `AlertDialog` primitive added in 8D. Do not add new UI primitives;
  docs/58 §2.4 states none are needed.

### 3.5 Pages

- **`app/(protected)/watchlists/page.tsx`** — **replace** the existing
  `EmptyState`-only placeholder (ADR-103). List of `WatchlistCard`s + create
  dialog. Keep a genuine empty state for the "user has no watchlists yet" case,
  reusing the shared `EmptyState` component.
- **`app/(protected)/watchlists/[id]/page.tsx`** (new) — detail view with
  add/remove assets. The asset picker reuses the asset-search half of
  `frontend/components/shared/symbol-timeframe-picker.tsx` (read it; extract or
  reuse rather than duplicating the search logic).

### 3.6 Navigation

**Do NOT add a nav item.** `Watchlists` already exists in
`frontend/components/layout/nav-config.ts:48` (it pointed at the placeholder).
Leave it exactly as-is.

### 3.7 Loading / error / empty states

Every page must handle loading, error, and empty consistently with Phase
7B/7C's established patterns — skeletons while loading, the shared error UI on
failure, `EmptyState` when there is genuinely nothing. Read a comparable page
(e.g. the Signals or Markets list page) and match it.

### 3.8 Documentation updates

- `docs/30_DEVELOPMENT_ROADMAP.md` — mark 7D-B Completed.
- `BACKLOG.md` — update §26; remove/adjust the stale "Watchlists remains a
  coming-soon placeholder (ADR-103)" note in §24, which is no longer true.
  Record any new gotcha you hit.
- `CHANGELOG.md` — entry matching the file's existing format.
- An **ADR is only needed if you make a real architectural decision** (e.g. if
  `AssetTable` needed a non-trivial change to be reusable). Straight application
  of docs/58 §2.4 needs no new ADR. Use judgment; if you write one, it is
  ADR-129 and must match the neighbouring ADRs' format.

---

## 4. Landmines — read these or you will lose time

1. **Do NOT change the backend's `PUT /watchlists/{id}` to `PATCH`** because the
   frontend client lacks `apiPut`. The fix is to add `apiPut` (§3.2). The verb
   is part of the contract shipped in 7D-A and documented in `docs/04` and
   `docs/58` §2.3. This is the single most likely wrong turn in this phase.

2. **There is no frontend test suite** — no Jest, Vitest, or Playwright anywhere
   in `frontend/` (BACKLOG §23/§24). Do not add one; that is its own decision,
   not a side effect of this phase. Verification is §5's commands plus manual
   checking.

3. **Do NOT run `npm run format:check`.** It fails on ~55 pre-existing files
   (BACKLOG §23) and has nothing to do with your changes. Do not reformat
   unrelated files. `npm run lint` is the CI-relevant check and is clean.

4. **Do not add per-asset analysis columns** to the watchlist asset table, no
   matter how natural it looks — see §1. `docs/21` describes a richer display;
   it is explicitly deferred.

5. **`item_count` comes from the list endpoint.** Do not call the detail
   endpoint per card to compute counts.

---

## 5. Verification — run these and report exact output

```
cd frontend && npm run typecheck
cd frontend && npm run lint
cd frontend && npm run build
```

All three must pass. If any fails, STOP and report rather than working around it.

**Manual check (required — there are no automated frontend tests).** The
backend must be running. Walk the full flow and report what you observed:
- empty state → create a watchlist → it appears with count 0
- open detail → add an asset → count and table update
- add the same asset again → conflict handled gracefully, no crash
- remove the asset → table updates
- rename the watchlist → new name shown in list and detail
- delete the watchlist → returns to list, gone
- reload mid-flow → state persists (it is server-backed, not local)

**Do NOT test against production.** Use the local dev environment. Note that
`backend/scripts/seed_dev_data.py` is the standard way to get real assets into
a fresh local DB (BACKLOG §24).

---

## 6. Done criteria

- All seven operations work from the UI, against the real backend.
- The ADR-103 placeholder is gone; `/watchlists` is real CRUD.
- `apiPut` added; no backend file modified.
- `typecheck`/`lint`/`build` all pass.
- No new UI primitives; `AssetTable` reused (additively if changed at all).
- docs/30, BACKLOG (§24 + §26), CHANGELOG updated.
- One commit, `feat:` prefix, message matching `git log --oneline -10` style,
  ending with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

---

## 7. Report back

What you built, exact typecheck/lint/build output, **what you actually observed
in the manual walkthrough** (not just "it works"), the commit SHA, and — most
importantly — **anything in this spec that turned out to be wrong about the
repo, or any judgment call you had to make.** If you disagree with something
here, say so rather than silently working around it. If a doc contradicts this
spec, the doc wins; stop and report the conflict.
