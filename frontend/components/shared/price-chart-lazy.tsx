"use client";

import dynamic from "next/dynamic";

import { ChartSkeleton } from "@/components/shared/skeletons";

/**
 * `lightweight-charts` is browser-only and sizable - loading `PriceChart`
 * via `next/dynamic` (no SSR) keeps it out of the initial JS bundle
 * (docs/05 §18's code-splitting goal). Import overlay *types* from
 * `./price-chart` directly (type-only imports don't pull runtime code).
 */
export const PriceChart = dynamic(() => import("./price-chart").then((mod) => mod.PriceChart), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});
