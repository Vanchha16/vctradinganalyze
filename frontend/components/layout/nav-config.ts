import {
  BarChart3,
  BookMarked,
  BrainCircuit,
  CalendarClock,
  Gauge,
  LayoutDashboard,
  LineChart,
  MessagesSquare,
  Newspaper,
  Settings as SettingsIcon,
  Signal,
  Terminal,
  UserRound,
  Waves,
  type LucideIcon,
} from "lucide-react";

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
    group: "Account",
    items: [
      { label: "Profile", href: "/profile", icon: UserRound },
      { label: "Settings", href: "/settings", icon: SettingsIcon },
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
