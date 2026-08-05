"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";

import { BrandMark } from "@/components/shared/brand-mark";
import { NAV_GROUPS } from "@/components/layout/nav-config";
import { useAuth } from "@/hooks/use-auth";
import { cn } from "@/lib/utils";

export function Sidebar({
  onNavigate,
  collapsed = false,
  onToggleCollapsed,
}: {
  onNavigate?: () => void;
  collapsed?: boolean;
  onToggleCollapsed?: () => void;
}) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const query = searchParams.toString();
  const { user } = useAuth();

  // Role-gated groups (e.g. "Admin") are hidden entirely for a user whose
  // role isn't listed - docs/59 §5.4/ADR-118, purely a UX convenience, the
  // real boundary is the backend's `require_admin`/`require_super_admin`.
  const visibleGroups = NAV_GROUPS.filter((g) => !g.roles || (user && g.roles.includes(user.role)));

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-14 shrink-0 items-center gap-2.5 px-4">
        <Link href="/dashboard" className="grid size-8 shrink-0 place-items-center rounded-lg bg-gradient-brand text-primary-foreground">
          <BrandMark className="size-4" />
        </Link>
        {!collapsed && (
          <Link href="/dashboard" className="min-w-0">
            <p className="truncate text-[13px] font-semibold tracking-tight">ClaudeTrading</p>
            <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-primary">AI Terminal</p>
          </Link>
        )}
        {onToggleCollapsed && (
          <button
            type="button"
            onClick={onToggleCollapsed}
            aria-label="Toggle sidebar"
            className="focus-ring ml-auto grid size-6 shrink-0 place-items-center rounded-md text-muted-foreground transition-colors hover:bg-sidebar-accent hover:text-foreground"
          >
            <svg viewBox="0 0 24 24" className="size-4 fill-none stroke-current stroke-2">
              <path d={collapsed ? "M9 6l6 6-6 6" : "M15 6l-6 6 6 6"} />
            </svg>
          </button>
        )}
      </div>

      <nav className="flex-1 space-y-5 overflow-y-auto px-3 py-3">
        {visibleGroups.map((g) => (
          <div key={g.group}>
            {!collapsed && (
              <p className="px-2.5 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted-foreground/70">
                {g.group}
              </p>
            )}
            <div className="space-y-0.5">
              {g.items.map((item) => {
                const isActive = pathname === item.href;
                const href = item.preserveQuery && query ? `${item.href}?${query}` : item.href;
                return (
                  <Link
                    key={item.href}
                    href={href}
                    title={item.label}
                    onClick={onNavigate}
                    className={cn(
                      "focus-ring group relative flex items-center gap-2.5 rounded-lg px-2.5 py-2 text-[13px] font-medium transition-all duration-200",
                      isActive
                        ? "bg-sidebar-accent text-foreground"
                        : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
                    )}
                  >
                    {isActive && (
                      <span className="absolute left-0 top-1/2 h-4 w-0.5 -translate-y-1/2 rounded-r-full bg-primary" />
                    )}
                    <item.icon className={cn("size-4 shrink-0 transition-colors", isActive ? "text-primary" : "group-hover:text-foreground")} />
                    {!collapsed && <span className="truncate">{item.label}</span>}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
    </div>
  );
}
