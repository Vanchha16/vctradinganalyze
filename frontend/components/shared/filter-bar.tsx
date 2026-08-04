import type { ReactNode } from "react";

/**
 * Layout/URL-sync plumbing only - domain-specific filter *contents*
 * (which selects, which options) stay in each feature folder and are
 * passed as children (docs/54 §4). Pair with `useQueryFilters`.
 */
export function FilterBar({ children }: { children: ReactNode }) {
  return <div className="mb-4 flex flex-wrap items-center gap-2">{children}</div>;
}

export function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="sr-only">{label}</label>
      {children}
    </div>
  );
}
