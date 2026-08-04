# Premium Design System

# 1. Scope

Phase 7D (two passes) already applied substantial visual polish across every page in this app - Geist typography, an informal spacing/motion vocabulary, `Card`'s `interactive` hover state, shaped skeletons, a reusable `ConfidenceGauge`, chart-card framing, mobile card views, and a first accessibility pass. This document is Phase 7E's deliverable: it formalizes those conventions into a written, cohesive system, closes the two real gaps the system had (no themeable radius variable, no `success`/`warning` color tokens), and defines the AI-first/chart-first principles this app's remaining redesign moves apply. It is frontend-only - no backend, API, schema, or auth file is affected by anything in this document.

---

# 2. Color System

The existing CSS custom properties (`app/globals.css`) are the source of truth and are **not renamed** - every Tailwind utility class in the app (`bg-background`, `text-foreground`, `border-primary`, etc.) depends on these exact names, and a rename would be a mechanical, high-file-count change for zero visual benefit:

| Token | Purpose |
|---|---|
| `--background` / `--foreground` | Page background / default text |
| `--card` / `--card-foreground` | Card surfaces |
| `--primary` / `--primary-foreground` | Brand accent (`#3B82F6`, docs/05 §4) |
| `--secondary` / `--secondary-foreground` | Neutral fill (hover states, secondary buttons) |
| `--destructive` / `--destructive-foreground` | Danger (`#EF4444`, docs/05 §4) |
| `--muted` / `--muted-foreground` | De-emphasized text/backgrounds |
| `--border` | All borders (`* { @apply border-border }`) |
| `--ring` | Focus rings |

**New in Phase 7E** - `--success` and `--warning` (+ `-foreground` pairs), defined identically in `:root` and `.dark` (docs/05's palette is dark-first and never specified separate light-mode success/warning shades - same precedent already applied to `--primary`):

| Token | Value (HSL) | Matches |
|---|---|---|
| `--success` | `142 71% 45%` | docs/05 §4's Success `#22C55E` |
| `--success-foreground` | `0 0% 100%` | White text on success fill |
| `--warning` | `38 92% 50%` | docs/05 §4's Warning `#F59E0B` |
| `--warning-foreground` | `0 0% 100%` | White text on warning fill |

This corrects a real drift: `Badge`'s `success` variant hardcoded `bg-green-600` (Tailwind's palette green, not docs/05's `#22C55E`), and half a dozen call sites (`ConfidenceGauge`, `EvidenceList`, `AnalysisSummary`, the Economic Calendar risk-window row) hardcoded raw `text-green-600`/`bg-amber-500`/`border-amber-500` Tailwind classes instead of a theme token. Phase 7E migrates all of these onto the new tokens (§8 below) - the visual output is intentionally near-identical (`--warning`'s value already matches current `amber-500` usage exactly; `--success` corrects `green-600` to docs/05's actual spec `#22C55E`), the fix is architectural (one token instead of six hardcoded copies), not cosmetic.

**Never introduced**: a fourth "info" or "neutral-accent" color - `--secondary` already covers that role everywhere it's needed; adding a token with no consumer would violate "don't introduce abstractions beyond what's needed."

---

# 3. Radius Scale

`app/globals.css` gains `--radius: 0.5rem` - matching `Card`'s current computed `rounded-lg` output exactly, so this is a non-visual change. `tailwind.config.ts`'s `borderRadius` extension maps the standard shadcn triple onto it:

```
lg: "var(--radius)"           /* containers: Card, Dialog, Sheet content */
md: "calc(var(--radius) - 2px)"  /* controls: Button, Input, Select trigger */
sm: "calc(var(--radius) - 4px)"  /* tight inline elements */
```

This project never adopted this convention (radius was hardcoded per-component as `rounded-lg`/`rounded-md` literals) - formalizing it means a future palette/density change only edits one variable. Existing conventions this codifies, unchanged in output:

- **Containers** (`Card`, `Dialog`, `Sheet`, chart-frame `<div>`): `rounded-lg`
- **Controls** (`Button`, `Input`, `Select` trigger, sort-header buttons): `rounded-md`
- **Pills/badges** (`Badge`, SMC overlay toggles, chat status chips): `rounded-full`
- **Chat bubble tail corner** (`message-thread.tsx`): `rounded-xl` base with `rounded-br-sm` (user) / `rounded-bl-sm` (assistant) - the one deliberate asymmetric-radius pattern in the app, signaling message direction.

---

# 4. Typography Scale

Geist (fallback Inter), self-hosted via `next/font/google` (`app/layout.tsx`), exposed as `--font-sans`/`--font-mono` CSS variables. The scale Phase 7C/7D already established, formalized here as the standard future components must match - **no font-size changes to any existing component**:

| Role | Classes | Used by |
|---|---|---|
| Page title | `text-2xl font-semibold tracking-tight` | `PageHeader` |
| Section header (marquee cards) | `text-base font-semibold` | `AnalysisSummary`'s "Summary" header, chart-card's "Price Chart" label |
| Card title (compact cards) | `text-sm font-semibold leading-none tracking-tight` | `CardTitle` default - widgets, signal cards, news cards |
| Body | `text-sm` | Default paragraph/label text app-wide |
| Caption | `text-xs text-muted-foreground` | Stat labels, timestamps, badge-adjacent metadata |
| Monospace (numeric) | `tabular-nums` (Geist Sans's tabular figures, not a separate mono font) | Prices, confidence scores, stat values |

---

# 5. Elevation

Three levels, all pre-existing Tailwind shadow utilities - no custom shadow tokens introduced, since Tailwind's scale already covers every case in use:

| Level | Class | Used for |
|---|---|---|
| Resting | `shadow-sm` | Static `Card` |
| Interactive | `shadow-md` (on hover) | `Card interactive`, `SignalCard`'s `whileHover` lift |
| Overlay | `shadow-lg` (Radix default) | `Dialog`, `Sheet` - handled by Radix's own styling, never set manually |

---

# 6. Motion Vocabulary

docs/05 §19 scopes Framer Motion to four categories: **page transitions, dialogs, dropdowns, cards**. Dialogs/dropdowns already get Radix's built-in `animate-in`/`animate-out` CSS animations - that satisfies the category without a second (Framer Motion) implementation of the same thing. Framer Motion in this app is used for the other two categories plus one component-level exception:

| Duration | Use | Where |
|---|---|---|
| `150ms` | Press/hover feedback | `Button`'s `active:scale-[0.98]`, `Card interactive`'s shadow transition |
| `200-250ms` | Page/section entrance fade | `PageContainer`'s fade-in, `AnalysisGuideStepper`'s connector fill |
| `700ms` | Emphasis fill (deliberate outlier) | `ConfidenceGauge`'s ring `stroke-dashoffset` transition - slow enough to read as a meaningful reveal, not a UI micro-interaction |
| `60ms` stagger | List entrance | Dashboard's 6-widget `staggerChildren` |

No exit animations, no gesture bindings, no scroll-triggered animation - matches docs/05 §19's "minimal" framing. Future motion work should reuse one of these four durations rather than inventing a fifth.

---

# 7. Component States

The convention every interactive element in this app follows, formalized from `Button`'s existing implementation:

```
hover:<bg-or-shadow-change>
active:scale-[0.98]                                  /* buttons only - press feedback */
focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring
disabled:pointer-events-none disabled:opacity-50
transition-colors | transition-shadow | transition-all duration-150
```

Any new interactive element (button, link-as-button, custom toggle) must include the `focus-visible` ring at minimum - this was the concrete gap Phase 7D's accessibility pass found and fixed on Sidebar links and dashboard widget rows.

---

# 8. Reuse Map

The mechanism that keeps this system cohesive going forward - before building something new, check this table:

| Need | Reuse | Path |
|---|---|---|
| A confidence/score ring | `ConfidenceGauge` (`size="sm"` for inline, default for hero) | `features/ai-analysis/components/confidence-gauge.tsx` |
| A clickable card row | `<Card interactive>` | `components/ui/card.tsx` |
| A dashboard widget | `WidgetCard` | `features/dashboard/components/widget-card.tsx` |
| A loading placeholder shaped like real content | `ListItemSkeleton`/`CardSkeleton`/`WidgetSkeleton`/`ChartSkeleton` | `components/shared/skeletons.tsx` |
| An enum → `Badge` variant mapping | `lib/badge-variants.ts` | `lib/badge-variants.ts` |
| SMC chart overlay data | `buildSmcOverlays`/`SmcOverlayToggles` | `lib/smc-overlays.ts`, `components/shared/smc-overlay-toggles.tsx` |
| AI-generated text rendering | `Markdown` (lazy-loaded) | `components/shared/markdown-lazy.tsx` |
| A price/OHLC chart | `PriceChart` (lazy-loaded) | `components/shared/price-chart-lazy.tsx` |
| A "this is AI-generated" marker | `AiBadge` (new, §9) | `components/shared/ai-badge.tsx` |

---

# 9. AI-First / Chart-First Principles

Two product principles this phase makes concrete:

**Chart-first**: `PriceChart` is the default hero visual element on any page that has trade-relevant price data - already true on Markets detail (2-column layout, chart spans 2/3), Signals detail, and AI Analysis detail. No page shows a price-relevant symbol without its chart being the largest visual element on that page.

**AI-first**: AI-generated content is visually marked as such, not presented identically to deterministic data. This mirrors an existing *backend* boundary (ADR-078/079: the recommendation/confidence/risk numbers are always deterministic; only the narrative reasoning text is LLM-generated) by making that boundary visible in the UI for the first time. New `AiBadge` component (compact `Badge` + sparkle icon + "AI" text) marks:

- `ReasoningSections`' tab header (the reasoning text is `AIAnalysisResponse`'s one AI-generated field per ADR-079)
- `MessageThread`'s assistant bubbles only - user bubbles are the human's own words and are never marked

This is a visual marker only - it adds no new data, no new backend call, and does not change which fields are deterministic vs. AI-generated (that boundary already existed; this phase makes it visible).

---

# 10. Explicitly Out of Scope

- Renaming `--background`/`--primary`/etc. - see §2.
- A fourth semantic color token beyond success/warning - see §2.
- Per-row sparkline/mini-charts on Dashboard widgets - would require additional per-row candle fetches for a "chart-first" gesture that doesn't fit a compact list row; the full `PriceChart` already carries this principle on every detail page.
- Icon-augmented color-only badges (e.g. a warning-triangle icon baked into every `importance`/`sentiment` badge) - a real accessibility improvement, but a large mechanical change across every `badge-variants.ts` consumer; deferred to a dedicated accessibility pass rather than bundled into this design-system phase.
- A full visual rewrite of Markets/Signals/AI Analysis/AI Chat page layouts - Phase 7D already delivered the 2-column Markets detail, the guided AI Analysis stepper, the redesigned chat bubbles, and mobile card views; this phase's remaining moves (§9, Dashboard hero weighting, News card unification) are the genuine gaps left, not a re-do.
