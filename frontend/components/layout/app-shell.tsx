"use client";

import { Suspense, useEffect, useState } from "react";

import { CommandPalette } from "@/components/layout/command-palette";
import { Sidebar } from "@/components/layout/sidebar";
import { TopNav } from "@/components/layout/top-nav";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

/**
 * Every page renders inside this shell. Desktop: persistent, collapsible
 * sidebar (`lg:` breakpoint). Mobile: `Sheet`-based slide-in drawer. Both
 * reuse the same `Sidebar` nav so there is exactly one source of truth for
 * the product's navigation.
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setPaletteOpen((p) => !p);
      }
      if (e.key === "Escape") setPaletteOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="pointer-events-none fixed inset-x-0 top-0 h-[420px] bg-glow" />

      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="glass w-[272px] max-w-[84vw] border-r border-border p-0 shadow-lift">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Suspense fallback={null}>
            <Sidebar onNavigate={() => setMobileNavOpen(false)} />
          </Suspense>
        </SheetContent>
      </Sheet>

      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 hidden flex-col border-r border-sidebar-border bg-sidebar transition-[width] duration-300 ease-[cubic-bezier(.22,1,.36,1)] lg:flex",
          collapsed ? "w-[68px]" : "w-[248px]",
        )}
      >
        <Suspense fallback={null}>
          <Sidebar collapsed={collapsed} onToggleCollapsed={() => setCollapsed((c) => !c)} />
        </Suspense>
      </aside>

      <div className={cn("transition-[padding] duration-300 lg:pl-[248px]", collapsed && "lg:pl-[68px]")}>
        <TopNav onOpenMobileNav={() => setMobileNavOpen(true)} onOpenSearch={() => setPaletteOpen(true)} />
        <main className="relative flex-1 px-4 py-6 md:px-6 lg:px-8">{children}</main>
      </div>
    </div>
  );
}
