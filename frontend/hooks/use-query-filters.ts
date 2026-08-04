"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useMemo } from "react";

type FilterValues = Record<string, string | undefined>;

/**
 * Generalizes `use-dashboard-selection.ts`'s URL-synced-state pattern for
 * an arbitrary set of filters (Markets/Signals/News/Economic Calendar
 * filter bars, docs/54 §3). Changing a filter resets `page` to 1 by
 * default - the current page's results are no longer meaningful once
 * the filter set changes.
 *
 * Returns `Record<string, string | undefined>` rather than a per-caller
 * generic type - callers cast individual fields to their specific enum
 * type at the call site (e.g. `filters.status as SignalStatus`), which
 * avoids TypeScript's structural-typing friction between named filter
 * interfaces and an indexed `Record` constraint.
 *
 * `defaults` should be a stable, module-level object (its keys define
 * which query params this hook reads/writes) - passing a fresh object
 * literal every render works but is wasteful, same expectation as any
 * React hook accepting a config object.
 */
export function useQueryFilters(defaults: FilterValues) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const filters = useMemo(() => {
    const result: FilterValues = { ...defaults };
    for (const key of Object.keys(defaults)) {
      const value = searchParams.get(key);
      if (value !== null) result[key] = value;
    }
    return result;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const page = Number(searchParams.get("page") ?? "1") || 1;

  const setFilters = useCallback(
    (next: FilterValues, options?: { resetPage?: boolean }) => {
      const params = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(next)) {
        if (value === undefined || value === "") {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      }
      if (options?.resetPage !== false) {
        params.delete("page");
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [pathname, router, searchParams],
  );

  const setPage = useCallback(
    (nextPage: number) => {
      const params = new URLSearchParams(searchParams.toString());
      if (nextPage <= 1) {
        params.delete("page");
      } else {
        params.set("page", String(nextPage));
      }
      router.push(`${pathname}?${params.toString()}`);
    },
    [pathname, router, searchParams],
  );

  return { filters, page, setFilters, setPage };
}
