# Frontend Foundation Architecture

# 1. Scope

Phase 7A builds the frontend's authentication and application-shell foundation - every future page (Markets, Signals, News, Watchlists, AI Analysis, Admin) builds on this. It is not a page-building phase; it is the layout, auth, theming, and shared-UI substrate those pages will reuse (this phase's brief §Objective).

See `docs/05_FRONTEND_GUIDELINES.md` for the product-level frontend vision this narrows, and ADR-099 through ADR-102 for the specific decisions made.

---

# 2. Reuse Map

| Requirement | Reused from |
|---|---|
| API request plumbing | `services/api-client.ts`'s `apiGet`/`ApiError` pattern, extended (not replaced) with auth headers and a `apiPost`/`apiDelete` counterpart |
| Layout primitives | `features/dashboard/components/page-container.tsx`, the existing `Sidebar`'s responsive structure |
| UI primitives | `components/ui/{button,card,badge,skeleton}.tsx` - extended with new primitives (dialog, dropdown-menu, avatar, label, input, form, separator, sheet), never duplicated |
| Data fetching | `providers/query-provider.tsx`'s `QueryClientProvider`, already configured project-wide |
| Existing dev pages | Technical Analysis/SMC/Market Regime pages remain as-is, relocated under the new authenticated shell (ADR-101), not rebuilt |

No parallel auth system, no second layout shell, no second toast/loading/error pattern - this phase extends what Phase 6's dev dashboard already established.

---

# 3. Auth State & Token Storage (ADR-099)

```
lib/auth/
  auth-store.ts        zustand store: { accessToken, user, status: "idle"|"loading"|"authenticated"|"unauthenticated" }
  auth-provider.tsx     mounts once (root layout); on mount, if a refresh token exists in localStorage,
                         calls POST /auth/refresh -> GET /auth/me to restore session; otherwise marks
                         status "unauthenticated"
  use-auth.ts           thin hook over the store: { user, status, login, register, logout }
services/auth.ts         POST /auth/register, /login, /refresh, /logout, GET /auth/me - thin wrappers,
                         no business logic (mirrors services/analysis.ts's shape)
```

- **Access token**: held in the zustand store only (memory) - never persisted, never written to `localStorage`/`sessionStorage`/cookies. Lost on full page reload; re-derived via refresh.
- **Refresh token**: persisted in `localStorage` under a single namespaced key. The only piece of session state that survives a reload.
- **`apiClient` (extended `services/api-client.ts`)**: attaches `Authorization: Bearer <accessToken>` when present; on a `401` with `error: "invalid_access_token"`, attempts exactly one silent refresh-and-retry before surfacing the failure (mirrors the backend's own "one retry, then fail gracefully" precedent, e.g. ADR-081) - never an infinite retry loop.
- **Route protection**: a `(protected)` route group's layout renders `null`/a full-screen loading state while `status === "loading"`, redirects to `/login` when `status === "unauthenticated"` (preserving the attempted path as a `?next=` query param for post-login redirect), and renders `children` once `status === "authenticated"`. A `(auth)` route group (login/register/forgot-password) does the inverse - already-authenticated users are redirected to `/dashboard`.

---

# 4. Pages (this phase)

```
app/
  (auth)/
    login/page.tsx
    register/page.tsx
    forgot-password/page.tsx      informational stub only (ADR-100) - no submission, no fake endpoint call
  (protected)/
    layout.tsx                     AppShell (Sidebar + TopNav + UserMenu), auth-gated
    dashboard/...                  existing pages, relocated here unchanged
```

`/reset-password` is not built this phase (ADR-100) - it has no reachable entry point without a working forgot-password email flow.

Forms use `react-hook-form` + `zod` schemas (`lib/validation/auth.ts`) mirroring the backend's own validation rules where they're user-facing (password: 12+ chars, docs/23 §7) - client-side validation is a UX convenience only, the backend remains the source of truth and every submission still surfaces real backend validation errors (`WeakPasswordException`, `DuplicateUserException`, etc. via `ApiError`).

---

# 5. Global Layout

```
components/layout/
  app-shell.tsx        composes Sidebar + TopNav, responsive (desktop: persistent sidebar; mobile: Sheet-based drawer)
  sidebar.tsx           extends the existing Sidebar - real product nav (docs/05 §7), role-aware
                         (Admin item only rendered for UserRole.ADMIN/SUPER_ADMIN, per docs/23 §12)
  top-nav.tsx           breadcrumb/page title slot + UserMenu
  user-menu.tsx         dropdown-menu: profile link, theme toggle, logout
```

`Sidebar` is extended in place (ADR-101), not duplicated - its existing active-link/responsive logic is preserved, only `NAV_ITEMS` and the "ClaudeTrading Dev" label change.

---

# 6. Shared UI (new this phase)

- `components/ui/{dialog,dropdown-menu,avatar,label,input,form,separator,sheet}.tsx` - shadcn/Radix primitives, same construction pattern as the existing `button.tsx`/`badge.tsx` (`cva` variants, `cn()` merging, `React.forwardRef`).
- `components/shared/empty-state.tsx` - generic empty-state (icon + message + optional action), reused by every future "no signals"/"no watchlist"/"no news" case (docs/05 §15) rather than one-off per page.
- `components/shared/error-page.tsx` - 404/500 full-page fallbacks (`app/not-found.tsx`, `app/error.tsx`), distinct from the existing per-card `ErrorCard` (which stays for widget-level API errors).
- Toast notifications via `sonner`'s `<Toaster />` mounted once in the root layout; a thin `lib/toast.ts` wrapper (`toast.success`/`toast.error`) so call sites never import `sonner` directly (same "one seam to swap later" precedent as `apiClient` wrapping `fetch`).

---

# 7. Theme System

`next-themes`'s `ThemeProvider` (`attribute="class"`, matching the already-configured `darkMode: ["class"]`) wraps the root layout, `defaultTheme="dark"` (docs/05 §3 "Dark mode first"). `globals.css` gains a `.dark { ... }` block; both the existing `:root` block and the new `.dark` block are aligned to docs/05 §4's actual palette (Primary `#3B82F6`, Success `#22C55E`, Warning `#F59E0B`, Danger `#EF4444`; dark-mode Background `#0B1220`, Card `#111827`, Border `#1F2937`, Text Primary `#F9FAFB`, Text Secondary `#9CA3AF`) - closing the gap BACKLOG.md §1 already tracks ("Tailwind color palette incomplete"). `UserMenu` exposes a light/dark/system toggle.

---

# 8. Responsive Layout

Breakpoints exactly as docs/05 §16: Mobile `<640px`, Tablet `640-1024px`, Desktop `1024px+`, Large Desktop `1440px+` - matching Tailwind's default `sm`/`lg`/`2xl` scale already in use (`lg:` breakpoint already drives the existing `Sidebar`'s desktop/mobile split). Mobile navigation uses a `Sheet` (slide-in drawer) rather than the persistent sidebar; a bottom nav (docs/05 §6) is deferred - not required for 7A's scope (no page-specific navigation exists yet to warrant one).

---

# 9. API Integration

Only already-existing endpoints are called: `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`. No new backend endpoints, no new backend code changes in this phase at all - Phase 7A is frontend-only.

---

# 10. Testing Strategy

Given this project has no established frontend test tooling yet (no Jest/Vitest/Playwright configured), and adding one is a real decision beyond this phase's "foundation" scope, Phase 7A is verified via: `npm run typecheck` (TypeScript strict mode), `npm run lint` (ESLint), `npm run build` (production build succeeds), and manual verification against the running backend (register -> login -> protected route -> refresh -> logout round-trip). Introducing a frontend test framework is flagged for a future phase, not decided here.

---

# 11. Out of Scope for Phase 7A

`/reset-password` (ADR-100); email verification pages (no backend support); Markets/Signals/News/Watchlists/AI Analysis page content (future phases, this is the shell they'll use); a BFF/httpOnly-cookie auth layer (ADR-099, revisit if XSS-hardening becomes a priority); session/device-management UI (backend has the service logic but no API route yet, docs/37 §6/§9); MFA; refresh-token rotation UI implications (backend doesn't rotate yet); a frontend automated test suite (§10); bottom mobile navigation (no page-specific nav to warrant one yet).
