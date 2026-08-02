"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { cn } from "@/lib/utils";

/**
 * The full docs/05_FRONTEND_GUIDELINES.md §7 product navigation
 * (Markets, Signals, News, Economic Calendar, AI Analysis, Watchlists,
 * Admin) is deliberately not listed here yet - those pages don't exist
 * yet (future phases build them). Linking to a page that returns 404
 * would be worse UX than a shorter, honest nav - mirrors this project's
 * backend precedent of never exposing an endpoint before the logic
 * behind it exists. Extend this list as each area ships its own page.
 */
const NAV_ITEMS = [
  { label: "Overview", href: "/dashboard" },
  { label: "Technical Analysis", href: "/dashboard/technical-analysis" },
  { label: "Smart Money Concepts", href: "/dashboard/smart-money-concepts" },
  { label: "Market Regime", href: "/dashboard/market-regime" },
  { label: "API Explorer", href: "/dashboard/api-explorer" },
];

export function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();

  return (
    <nav className="flex h-full w-full flex-col gap-1 border-border p-4 lg:w-56 lg:border-r">
      <Link href="/dashboard" className="mb-4 px-2 text-sm font-semibold tracking-tight">
        ClaudeTrading AI
      </Link>
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        const href = query ? `${item.href}?${query}` : item.href;
        return (
          <Link
            key={item.href}
            href={href}
            onClick={onNavigate}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-secondary",
              isActive ? "bg-secondary text-secondary-foreground" : "text-muted-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
