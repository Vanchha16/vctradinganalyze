"use client";

import dynamic from "next/dynamic";

/**
 * `react-markdown` + `remark-gfm` (ADR-108) loaded via `next/dynamic` to
 * keep them out of the initial JS bundle (docs/05 §18) - most pages
 * never render markdown at all. `next/dynamic` caches the loaded module
 * after the first mount, so repeated `<Markdown>` instances in a single
 * message thread don't each re-fetch the chunk.
 */
export const Markdown = dynamic(() => import("./markdown").then((mod) => mod.Markdown), {
  loading: () => <div className="h-4 w-2/3 animate-pulse rounded bg-muted" />,
});
