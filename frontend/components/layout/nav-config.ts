import {
  BarChart3,
  BookMarked,
  BrainCircuit,
  Calculator,
  CalendarClock,
  Coins,
  FileClock,
  Gauge,
  Landmark,
  LayoutDashboard,
  LineChart,
  MessagesSquare,
  Newspaper,
  PieChart,
  Server,
  Settings as SettingsIcon,
  ShieldCheck,
  Signal,
  Terminal,
  TrendingUp,
  UserRound,
  Users,
  Waves,
  type LucideIcon,
} from "lucide-react";

import type { UserRole } from "@/services/types";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Only the single-symbol Analysis pages share URL-synced symbol/timeframe state (`use-dashboard-selection.ts`). */
  preserveQuery?: boolean;
}

export interface NavGroup {
  group: string;
  items: NavItem[];
  /** Group is hidden entirely unless the current user's role is in this list (Phase 8D, docs/59 §5.4/ADR-118) - omitted means visible to everyone. */
  roles?: UserRole[];
}

/** Same destinations as before (docs/05 §7) - only the visual grouping changed to match the reference UI's four labeled sections. */
export const NAV_GROUPS: NavGroup[] = [
  {
    group: "Trading",
    items: [
      { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
      { label: "Markets", href: "/markets", icon: BarChart3 },
      { label: "Watchlists", href: "/watchlists", icon: BookMarked },
      { label: "Technical Analysis", href: "/dashboard/technical-analysis", icon: LineChart, preserveQuery: true },
    ],
  },
  {
    group: "Intelligence",
    items: [
      { label: "AI Analysis", href: "/ai-analysis", icon: BrainCircuit },
      { label: "Signals", href: "/signals", icon: Signal },
      { label: "AI Chat", href: "/ai-chat", icon: MessagesSquare },
      { label: "Smart Money", href: "/dashboard/smart-money-concepts", icon: Waves, preserveQuery: true },
      { label: "Market Regime", href: "/dashboard/market-regime", icon: Gauge, preserveQuery: true },
    ],
  },
  {
    group: "Research",
    items: [
      { label: "News", href: "/news", icon: Newspaper },
      { label: "Economic Calendar", href: "/economic-calendar", icon: CalendarClock },
      { label: "API Explorer", href: "/dashboard/api-explorer", icon: Terminal, preserveQuery: true },
    ],
  },
  {
    group: "Tools",
    items: [
      { label: "Profit Split", href: "/tools/profit-split", icon: PieChart },
      { label: "Position Size", href: "/tools/position-size", icon: Calculator },
    ],
  },
  {
    group: "Account",
    items: [
      { label: "Profile", href: "/profile", icon: UserRound },
      { label: "Settings", href: "/settings", icon: SettingsIcon },
    ],
  },
  {
    group: "Admin",
    roles: ["admin", "super_admin"],
    items: [
      { label: "Admin Dashboard", href: "/admin", icon: ShieldCheck },
      { label: "Users", href: "/admin/users", icon: Users },
      { label: "Symbols", href: "/admin/assets", icon: Coins },
      { label: "Audit Logs", href: "/admin/audit-logs", icon: FileClock },
      { label: "System Health", href: "/admin/system-health", icon: Server },
      { label: "API Usage", href: "/admin/api-usage", icon: Terminal },
      { label: "Signal Statistics", href: "/admin/signal-statistics", icon: TrendingUp },
      { label: "Broker Orders", href: "/admin/orders", icon: Landmark },
      { label: "Admin Settings", href: "/admin/settings", icon: SettingsIcon },
    ],
  },
];

export const FLAT_NAV: NavItem[] = NAV_GROUPS.flatMap((g) => g.items);

/** Longest-prefix match first (e.g. "/dashboard/technical-analysis" before "/dashboard") since several routes nest under `/dashboard`. */
const BY_LONGEST_HREF = [...FLAT_NAV].sort((a, b) => b.href.length - a.href.length);

export function sectionLabel(pathname: string): string | null {
  const match = BY_LONGEST_HREF.find((i) => pathname.startsWith(i.href));
  return match ? match.label : null;
}
