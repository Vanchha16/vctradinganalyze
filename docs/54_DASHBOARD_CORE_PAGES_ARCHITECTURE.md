# Dashboard & Core Pages Architecture

# 1. Scope

Phase 7B builds the ten core product pages on top of Phase 7A's foundation (`AppShell`, auth, theming, shared UI, `apiClient`, TanStack Query, zustand). It is a frontend-only phase - no new backend endpoints, no backend code changes. Four areas have little or no backend support (Watchlists, Profile, Settings, live/drawing-tools chart features) and ship intentionally scoped down, per ADR-103 through ADR-105 - see those for the full reasoning.

---

# 2. Reuse Map

| Requirement | Reused from |
|---|---|
| Auth-gated routing, redirect, session | Phase 7A's `AuthGuard`/`(protected)` route group - every new page lives inside it, unmodified |
| Shell (Sidebar/TopNav/UserMenu) | Phase 7A's `AppShell` - `Sidebar`'s `NAV_ITEMS` extended with the new pages |
| Theming | Phase 7A's `next-themes` setup - the new chart component reads `resolvedTheme` for series colors |
| API client | Phase 7A's `apiGet`/`apiPost`/`apiDelete` (Bearer injection, refresh-on-401) - every new service module reuses it unmodified |
| Data fetching | The existing `hooks/use-assets.ts`/`use-technical-analysis.ts` pattern (TanStack Query wrapper per service call) - extended with one hook file per new query/mutation |
| URL-synced filter state | `hooks/use-dashboard-selection.ts`'s pattern, generalized into a reusable `use-query-filters.ts` for Markets/Signals/News/Calendar filter bars |
| Cards/Badges/Skeletons/Empty/Error UI | `components/ui/*` and `components/shared/*` from Phase 6/7A - extended with new primitives only where genuinely missing (Table, Tabs, Tooltip, Textarea, Pagination) |

No page reimplements API calling, auth gating, or layout - every one is new *content* inside the existing shell.

---

# 3. New Shared UI Primitives (`components/ui/`)

- `table.tsx` - standard `Table`/`TableHeader`/`TableBody`/`TableRow`/`TableHead`/`TableCell`, same construction pattern as every existing primitive (`cn()`, `React.forwardRef`). Used by Markets (asset list) and Economic Calendar (tabular event data) - genuinely table-shaped data, unlike Signals/News, which use cards (docs/05 §11's Signal Card, and an equivalent News Card).
- `tabs.tsx` - wraps `@radix-ui/react-tabs` (already an installed, unused dependency since before Phase 7A). Used by the AI Analysis page to organize docs/05 §12's sections (Technical/SMC/News/Economic/Risk) without one very long scroll.
- `tooltip.tsx` - new dependency `@radix-ui/react-tooltip`, same shadcn construction pattern. Used for score-breakdown/confidence explanations where a compact number needs a longer explanation on hover.
- `textarea.tsx` - native `<textarea>`, mirrors `input.tsx` exactly. Used by AI Chat's message composer.
- `pagination.tsx` - a small, dependency-free prev/next + page-count component (not a Radix primitive - there isn't one). Used by Signals/News/Calendar/AI Analysis history lists, all of which already return `{page, limit, total}` from their backend list endpoints.

`Modal`/`Drawer` (docs/05 §8) map directly onto Phase 7A's existing `Dialog`/`Sheet` - no new primitive needed. `Breadcrumb` and `Command Palette` are deferred (§9) - this project's navigation is currently single-level (no nested hierarchy a breadcrumb trail would clarify), and a command palette is a substantial standalone feature no page in this phase's brief requires.

---

# 4. New Shared Components (`components/shared/`)

- `page-header.tsx` - title + optional description + optional actions slot, used by all ten pages instead of one-off headers per page.
- `filter-bar.tsx` - a horizontal flex wrapper for a row of `Select`s/inputs, paired with `use-query-filters.ts` for URL-synced state. Domain-specific filter *contents* (which selects, which options) stay in each feature folder; this component is only the layout/URL-sync plumbing.
- `price-chart.tsx` - the `lightweight-charts` wrapper (ADR-105): candlesticks + timeframe switcher + optional support/resistance/order-block price-line overlays + theme sync. Shared between Markets' asset detail page and the AI Analysis page's "Charts" section (docs/05 §12).
- `lib/badge-variants.ts` - centralizes the `Recommendation`/`SignalStatus`/`ConfidenceLevel`/`RiskLevel`/`NewsSentiment`/`EconomicImportance`/`MarketRegimeState` → `Badge` variant mappings that were previously inlined ad hoc in the Phase 6 dev-dashboard's `page.tsx` (`TREND_VARIANT`/`STRUCTURE_VARIANT`/`REGIME_VARIANT`) - every page showing one of these enums reuses the same mapping instead of redefining it.
- `lib/format.ts` - `formatDateTime`/`formatRelativeTime`/`formatPrice`/`formatPercent` using native `Intl` (no new date-formatting dependency - `Intl.DateTimeFormat`/`Intl.RelativeTimeFormat` are sufficient for this project's needs).

---

# 5. Per-Domain Feature Folders (`features/`)

One folder per page domain, following `features/auth`'s established shape (components colocated with the feature, hooks/services live at the top level per the existing project convention):

```
features/
  dashboard/       (existing, extended: new widget components)
  markets/         AssetTable, AssetFilterBar
  signals/         SignalCard, SignalFilterBar, BookmarkButton
  news/            NewsCard, NewsFilterBar
  economic-calendar/  CalendarTable, CalendarFilterBar
  ai-analysis/     AnalysisSummary, ReasoningSections, EvidenceList
  ai-chat/         ConversationList, MessageThread, MessageComposer
  watchlists/      (no components - EmptyState reused directly, per ADR-103)
  profile/         ProfileSummary
  settings/        AppearanceSection, AccountSection
```

`SignalCard` (docs/05 §11: asset, recommendation, confidence, risk, entry/stop/target, timeframe, reasoning, status) is built once in `features/signals/` and reused by the Dashboard's "Latest Signals" widget - cross-feature import, same precedent as backend modules reusing each other across domain boundaries (e.g. `dependencies/ai_chat.py` reusing `dependencies/ai_orchestrator.py`).

---

# 6. New Services (`services/`)

One file per domain, mirroring `services/analysis.ts`/`services/auth.ts`'s existing shape (thin functions wrapping `apiGet`/`apiPost`/`apiDelete`, no business logic):

`market-data.ts` (asset detail, candles, latest, indicators), `signals.ts`, `news.ts`, `calendar.ts`, `ai-analysis.ts`, `ai-chat.ts` (conversations/messages - Phase 7A built auth only, not this). `services/analysis.ts` (Technical/SMC/Market Regime, used by the existing dev pages) is untouched.

---

# 7. Routes

```
app/(protected)/
  dashboard/page.tsx        REPLACED - see §8
  markets/page.tsx          asset list + filters
  markets/[symbol]/page.tsx  chart + latest quote + indicators, links to the existing
                              technical-analysis/smart-money-concepts/market-regime pages
                              for that symbol (reuse, not duplication)
  ai-analysis/page.tsx      generate (symbol/timeframe picker) + most recent result
  ai-analysis/[id]/page.tsx  a persisted analysis, permalink from history
  signals/page.tsx          list + filters + generate
  signals/[id]/page.tsx     signal detail
  news/page.tsx             list + filters
  news/[id]/page.tsx        article detail
  economic-calendar/page.tsx table + filters
  ai-chat/page.tsx           conversation list + empty/new-conversation state
  ai-chat/[id]/page.tsx      a specific conversation's thread
  watchlists/page.tsx        coming-soon placeholder (ADR-103)
  profile/page.tsx           read-only account info (ADR-104)
  settings/page.tsx          appearance + account + logout (ADR-104)
  dashboard/technical-analysis, smart-money-concepts, market-regime, api-explorer
                              UNCHANGED from Phase 7A - still reachable, still real
```

---

# 8. Dashboard Page Replacement

The current `/dashboard` (a single-symbol Technical/SMC/Regime summary combo, built in Phase 6 as the dev dashboard's only page) is superseded by the real product Dashboard, built from independent, reusable widgets (docs/05 §9: Market Overview, Latest Signals, Economic Events, Breaking News, AI Insights - Portfolio Summary/Watchlist omitted, ADR-106). This is not a capability loss - Technical Analysis/SMC/Market Regime/API Explorer remain fully reachable, regrouped under a dedicated "Analysis" section in `Sidebar` rather than flattened at the top level (per explicit approval) - see §11.

---

# 11. Sidebar Navigation Structure

`Sidebar` (Phase 7A) is extended from a flat list to a grouped structure - an optional `section` label per nav item, rendered as a small uppercase heading above its group:

```
Dashboard
Markets
Signals
News
Economic Calendar
AI Analysis
AI Chat
Watchlists

Analysis
  Technical Analysis
  Smart Money Concepts
  Market Regime
  API Explorer

Profile
Settings
```

The "Analysis" section preserves the Phase 6 dev pages' visibility and existing URLs (`/dashboard/technical-analysis` etc.) unchanged - only their position in the nav changes, from a flat list to a labeled group, keeping them discoverable rather than demoted.

---

# 9. Testing Strategy

Same as Phase 7A (§10 of docs/53) - no frontend test framework exists yet, verified via `npm run typecheck`/`lint`/`build` plus manual browser-driven verification of each page against the real running backend. Introducing a frontend test framework remains a deferred, separate decision.

A real bug was caught during this manual verification, not just implementation: `PriceChart`'s original `autoSize: true` option internally wires a `ResizeObserver` that can still fire (attempting to paint into an already-disposed canvas, throwing `"Object is disposed"`) after `chart.remove()` runs in the cleanup effect, if a resize is queued right as the component unmounts (e.g. fast route navigation away from a chart page). Fixed by manually managing the `ResizeObserver` and explicitly disconnecting it *before* calling `chart.remove()`, eliminating the race - `components/shared/price-chart.tsx` documents this inline.

---

# 10. Out of Scope for Phase 7B

Watchlists CRUD (ADR-103); Profile/Settings edit forms (ADR-104); chart drawing tools, live/streaming updates, fullscreen (ADR-105); a real `GET /dashboard` backend endpoint (ADR-106); Notifications, Telegram, Subscription, Admin pages (no backend exists for any of them, same category of gap as Watchlists - not part of this phase's ten named pages); Command Palette; breadcrumb navigation; any backend changes.
