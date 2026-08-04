"use client";

import { Command, Menu, Search } from "lucide-react";

import { BrandMark } from "@/components/shared/brand-mark";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { UserMenu } from "@/components/layout/user-menu";

export function TopNav({
  onOpenMobileNav,
  onOpenSearch,
}: {
  onOpenMobileNav: () => void;
  onOpenSearch: () => void;
}) {
  return (
    <header className="glass sticky top-0 z-30 border-b border-border/70">
      <div className="flex h-14 items-center gap-3 px-4 md:px-6">
        <button
          type="button"
          onClick={onOpenMobileNav}
          aria-label="Open navigation menu"
          className="focus-ring grid size-9 shrink-0 place-items-center rounded-lg border border-border bg-surface text-muted-foreground transition-colors hover:text-foreground lg:hidden"
        >
          <Menu className="size-4" />
        </button>

        <div className="flex items-center gap-2 lg:hidden">
          <div className="grid size-7 place-items-center rounded-lg bg-gradient-brand text-primary-foreground">
            <BrandMark className="size-3.5" />
          </div>
          <span className="text-[13px] font-semibold">ClaudeTrading</span>
        </div>

        <button
          type="button"
          onClick={onOpenSearch}
          aria-label="Open search"
          className="focus-ring hidden w-[260px] items-center gap-2 rounded-lg border border-border bg-surface px-3 py-1.5 text-xs text-muted-foreground transition-all duration-300 ease-[cubic-bezier(.22,1,.36,1)] hover:w-[420px] hover:border-primary/30 hover:text-foreground md:flex"
        >
          <Search className="size-3.5" />
          Search screens…
          <kbd className="ml-auto flex items-center gap-0.5 rounded border border-border px-1 py-0.5 text-[10px]">
            <Command className="size-2.5" />K
          </kbd>
        </button>

        <div className="ml-auto flex items-center gap-2">
          <ThemeToggle />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
