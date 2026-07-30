# Frontend Guidelines

Version: 1.0

---

# 1. Objective

Build a premium SaaS experience comparable to:

- TradingView
- Linear
- Stripe Dashboard
- Vercel Dashboard
- Apple
- Bloomberg Terminal (simplified)

The UI must feel:

- Fast
- Modern
- Clean
- Professional
- Minimal
- Data-focused

---

# 2. Technology Stack

Framework

- Next.js 15+
- React 19
- TypeScript

UI

- Tailwind CSS
- shadcn/ui
- Radix UI
- Framer Motion
- Lucide Icons

Charts

- TradingView Advanced Charts
- Lightweight Charts (optional)

Forms

- React Hook Form
- Zod

Data

- TanStack Query
- Zustand

Theme

- next-themes

---

# 3. Design Principles

Every page should be:

✔ Responsive

✔ Accessible

✔ Fast

✔ Keyboard friendly

✔ Dark mode first

✔ Consistent spacing

✔ Minimal animations

---

# 4. Color Palette

Primary

#3B82F6

Success

#22C55E

Warning

#F59E0B

Danger

#EF4444

Background

#0B1220

Card

#111827

Border

#1F2937

Text Primary

#F9FAFB

Text Secondary

#9CA3AF

---

# 5. Typography

Font

Geist

Fallback

Inter

Headings

Bold

Body

Regular

Use consistent spacing.

---

# 6. Layout

Desktop

Sidebar

Top Navigation

Main Content

Right Information Panel

Mobile

Bottom Navigation

Drawer Menu

Responsive Cards

---

# 7. Navigation

Dashboard

Markets

Signals

News

Economic Calendar

AI Analysis

Watchlists

Profile

Settings

Admin

---

# 8. Reusable Components

Button

Card

Badge

Input

Textarea

Dialog

Dropdown

Tabs

Table

Pagination

Modal

Drawer

Toast

Tooltip

Skeleton Loader

Avatar

Breadcrumb

Command Palette

---

# 9. Dashboard Widgets

Market Overview

Latest Signals

Watchlist

Economic Events

Breaking News

Top Movers

AI Insights

Portfolio Summary (future)

---

# 10. Trading Chart

Must support

Multi Timeframe

Indicators

Drawing Tools

Fullscreen

Theme Sync

Live Updates

Signal Overlay

SMC Overlay

---

# 11. Signal Card

Display

Asset

Recommendation

Confidence

Risk

Entry

Stop Loss

Take Profit

Timeframe

Reasoning

Status

---

# 12. AI Analysis Page

Sections

Market Summary

Technical Analysis

SMC Analysis

News Sentiment

Economic Events

Recommendation

Confidence

Risk Assessment

Charts

Historical Comparison

---

# 13. Loading States

Every API request must show

Skeleton UI

Loading Spinner (only where necessary)

Optimistic Updates

---

# 14. Error States

Friendly error messages.

Retry button.

Fallback UI.

---

# 15. Empty States

No Signals

No Watchlist

No Notifications

No News

Each should guide the user toward the next action.

---

# 16. Responsive Breakpoints

Mobile

<640px

Tablet

640–1024px

Desktop

1024px+

Large Desktop

1440px+

---

# 17. Accessibility

WCAG AA

Keyboard navigation

Visible focus

ARIA labels

High contrast

---

# 18. Performance Goals

First Load < 2 seconds

Lighthouse > 90

Lazy Loading

Code Splitting

Image Optimization

Prefetch Routes

---

# 19. Animation

Framer Motion

Use only for

Page transitions

Dialogs

Dropdowns

Cards

Avoid excessive animation.

---

# 20. Folder Structure

frontend/

app/

components/

features/

hooks/

lib/

providers/

services/

store/

styles/

types/

utils/

assets/

---

# 21. Coding Standards

Use TypeScript strict mode.

No inline styles.

No duplicated components.

Reusable UI first.

Business logic stays outside components.

Server Components by default.

Client Components only when required.

---

# 22. Future Features

AI Chat Assistant

Portfolio Dashboard

Strategy Builder

Backtesting UI

Trade Journal

Broker Integration

Multi-language

PWA

Desktop App
