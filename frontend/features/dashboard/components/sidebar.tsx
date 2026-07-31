"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Technical Analysis", href: "/dashboard/technical-analysis" },
  { label: "Smart Money Concepts", href: "/dashboard/smart-money-concepts" },
  { label: "Market Regime", href: "/dashboard/market-regime" },
  { label: "API Explorer", href: "/dashboard/api-explorer" },
];

export function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();

  return (
    <nav className="flex w-full flex-col gap-1 border-border p-4 lg:w-56 lg:border-r">
      <p className="mb-2 px-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
        ClaudeTrading Dev
      </p>
      {NAV_ITEMS.map((item) => {
        const isActive = pathname === item.href;
        const href = query ? `${item.href}?${query}` : item.href;
        return (
          <Link
            key={item.href}
            href={href}
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
