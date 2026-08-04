# Frontend Experience & Advanced Trading UI Architecture

# 1. Scope

Phase 7C is a UX-polish pass over Phase 7B's ten core pages - frontend-only, zero new backend endpoints, no backend code changes. Every objective is additive UI work inside the `features/{domain}/` + `services/{domain}.ts` + hooks pattern docs/54 established. Three points genuinely extend shared architecture and are recorded as ADR-107 through ADR-109 - see those for the full reasoning; this document is the reuse map and component inventory.

---

# 2. Reuse Map

| Requirement | Reused from |
|---|---|
| Chart rendering, timeframe switcher, theme sync | Phase 7B's `PriceChart` (`lightweight-charts`) - extended, not replaced, with `zones`/`markers` props (ADR-107) |
| Badge/enum styling | `lib/badge-variants.ts` - `confidenceLevelVariant` reused by the new `ConfidenceGauge`; no new mapping functions added |
| URL-synced filter/sort/page state | `hooks/use-query-filters.ts` - Markets' new sort/search state and AI Chat's new status/search state both reuse it unmodified |
| SMC analysis data | `hooks/use-smc-analysis.ts` (`GET /analysis/smc/{symbol}`) - already returned BOS/CHoCH/Order Blocks/FVG/Liquidity Zones/Sweeps in full; nothing new was fetched, only newly *rendered* |
| Signal trade-setup/status fields | `SignalResponse.{triggered_at,closed_at,profit_loss}` - existed since Phase 6B, simply weren't rendered anywhere until `SignalStatusTimeline` |
| Conversation archive/delete | `hooks/use-conversation-actions.ts` (`useArchiveConversation`/`useDeleteConversation`) - existed since Phase 6C/7B, unused by any UI until `ConversationList`'s new dropdown |

No page reimplements data fetching, auth gating, or layout - every change is new content or a new prop on an existing shared component.

---

# 3. `PriceChart` Overlay Model Extension (ADR-107)

`components/shared/price-chart.tsx` gained two new optional props alongside the existing `overlays: PriceLineOverlay[]`:

- `zones?: ZoneOverlay[]` (`{high, low, color, label}`) - a price *range*, rendered as a paired top/bottom `createPriceLine()` call. Used for Order Blocks (`zone_high`/`zone_low`) and Fair Value Gaps (`gap_high`/`gap_low`).
- `markers?: ChartMarkerOverlay[]` (`{time, position: "aboveBar"|"belowBar", color, shape, text}`) - a point-in-time event, rendered via the native `createSeriesMarkers(series, markers)` plugin (`lightweight-charts` v5). Used for BOS (`break_time`, exact `break_price` available but deliberately unused - see ADR-107's Alternatives) and CHoCH (`confirmation_time`, no price field at all).

`lib/smc-overlays.ts`'s `buildSmcOverlays(smc, enabledKinds)` maps a full `SMCAnalysisResponse` to `{zones, markers, lines}` in one place - `lines` (plain `PriceLineOverlay[]`) covers Liquidity Zones, which are a single price level, not a range or a discrete event. Every kind is capped at the top 3 (by `strength_score`/`touch_count`), mirroring Phase 7B's original "top 3 Order Blocks" convention.

`components/shared/smc-overlay-toggles.tsx` is a small checkbox-group (rendered as clickable `Badge`s) so a page doesn't dump every overlay kind onto the chart by default - `DEFAULT_SMC_OVERLAYS` (`order_blocks`, `bos`) is the starting state everywhere it's used.

Used by: Markets detail (`markets/[symbol]/page.tsx`), AI Analysis detail (`ai-analysis/[id]/page.tsx`), Signal detail (`signals/[id]/page.tsx`) - all three now share the exact same overlay-building/toggle code instead of three separate implementations.

`PriceChart` itself moved behind `next/dynamic` (`components/shared/price-chart-lazy.tsx`, `ssr: false`) - `lightweight-charts` is a sizable, browser-only dependency that previously loaded on every page that imported `PriceChart` even before any chart-bearing route was visited.

---

# 4. Markdown Rendering (ADR-108)

`components/shared/markdown.tsx` wraps `react-markdown` + `remark-gfm` with manual Tailwind `components` overrides (no `@tailwindcss/typography` - not installed, not needed for the element types LLM output actually produces). `components/shared/markdown-lazy.tsx` wraps it again in `next/dynamic` for the same initial-bundle reason as `PriceChart`.

Used by:
- `features/ai-analysis/components/reasoning-sections.tsx` - each of the seven reasoning tabs (`summary`/`technical`/`smc`/`news`/`economic`/`risk`/`conclusion`)
- `features/ai-chat/components/message-thread.tsx` - assistant messages only; user messages stay plain `whitespace-pre-wrap` text

No `rehype-raw` anywhere - raw HTML is never rendered, regardless of source.

---

# 5. New/Changed Shared Components (`components/shared/`)

- `price-chart-lazy.tsx`, `markdown-lazy.tsx` - `next/dynamic` wrappers, §3/§4.
- `smc-overlay-toggles.tsx` - §3.
- `markdown.tsx` - §4.

---

# 6. Per-Domain Feature Changes (`features/`)

```
features/
  markets/          AssetTable (sortable headers, quick-action links), AssetFilterBar (+search)
  ai-analysis/       + AnalysisGuideStepper, ConfidenceGauge
                      EvidenceList (rewritten: timeline layout, same 4 groups)
                      ReasoningSections (+ Markdown)
  ai-chat/           ConversationList (+ archive/delete dropdown)
                      MessageThread (+ pendingUserContent/showTypingIndicator, + Markdown)
                      MessageComposer (+ prefill prop)
                      + SuggestedPrompts
  signals/           SignalFilterBar (+ symbol filter)
                      SignalCard (+ profit_loss badge)
                      + SignalStatusTimeline
  dashboard/         + QuickActionsWidget (6th widget)
```

`lib/smc-overlays.ts` sits at the `lib/` level (not a feature folder) since three different feature domains' pages consume it (§3).

---

# 7. ADR Summary

- **ADR-107** - `PriceChart` overlay model extended with zones (paired price lines) and time markers (native `createSeriesMarkers`) for SMC concepts. ADR-105's boundaries (no drawing tools, no live updates, no fullscreen) are unchanged - this only adds programmatic, server-data-driven overlay *types*.
- **ADR-108** - `react-markdown` + `remark-gfm` adopted for AI-generated text (Analysis reasoning, Chat messages). No `rehype-raw`.
- **ADR-109** - AI Chat "streaming-ready" via an optimistic pending-message placeholder (`MessageThread`'s `pendingUserContent`/`showTypingIndicator`), not real token streaming - the backend has no SSE/WebSocket. The component contract is shaped so a future streaming backend wouldn't require a rewrite, only a different way of populating the pending item.

---

# 8. Out of Scope

Unchanged from Phase 7B's ADR-103/104/105/106 and the roadmap: Watchlists CRUD backend, Profile/Settings edit forms, chart drawing tools, live/streaming chart or chat data, a real `GET /dashboard` endpoint, Admin/session-management/Notifications/Telegram/Subscription pages, a frontend automated test suite, and any new backend endpoint.

---

# 9. Testing Strategy

Same as Phase 7A/7B: no frontend test framework yet. Verified via `npm run typecheck`/`lint`/`build` plus manual browser-driven verification against the real running backend (seeded via `backend/scripts/seed_dev_data.py`).
