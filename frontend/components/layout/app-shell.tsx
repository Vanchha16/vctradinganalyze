"use client";

import { Suspense, useState } from "react";

import { Sidebar } from "@/components/layout/sidebar";
import { TopNav } from "@/components/layout/top-nav";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";

/**
 * Every future page renders inside this shell (this phase's stated
 * objective, docs/53 §5). Desktop: persistent sidebar (`lg:` breakpoint,
 * matching docs/05 §16). Mobile: `Sheet`-based slide-in drawer rather
 * than a persistent sidebar or bottom nav (docs/53 §8 - no page-specific
 * navigation exists yet to warrant a bottom nav).
 */
export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <div className="hidden lg:block">
        <Suspense fallback={null}>
          <Sidebar />
        </Suspense>
      </div>

      <Sheet open={mobileNavOpen} onOpenChange={setMobileNavOpen}>
        <SheetContent side="left" className="w-64 p-0">
          <SheetTitle className="sr-only">Navigation</SheetTitle>
          <Suspense fallback={null}>
            <Sidebar onNavigate={() => setMobileNavOpen(false)} />
          </Suspense>
        </SheetContent>
      </Sheet>

      <div className="flex min-h-screen flex-1 flex-col">
        <TopNav onOpenMobileNav={() => setMobileNavOpen(true)} />
        <main className="flex-1">{children}</main>
      </div>
    </div>
  );
}
