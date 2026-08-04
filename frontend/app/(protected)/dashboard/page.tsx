"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/shared/page-header";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { AiInsightsWidget } from "@/features/dashboard/components/ai-insights-widget";
import { BreakingNewsWidget } from "@/features/dashboard/components/breaking-news-widget";
import { EconomicEventsWidget } from "@/features/dashboard/components/economic-events-widget";
import { LatestSignalsWidget } from "@/features/dashboard/components/latest-signals-widget";
import { MarketOverviewWidget } from "@/features/dashboard/components/market-overview-widget";
import { QuickActionsWidget } from "@/features/dashboard/components/quick-actions-widget";
import { useAuth } from "@/hooks/use-auth";

const WIDGETS = [
  MarketOverviewWidget,
  LatestSignalsWidget,
  QuickActionsWidget,
  EconomicEventsWidget,
  BreakingNewsWidget,
  AiInsightsWidget,
];

const container = {
  hidden: {},
  show: { transition: { staggerChildren: 0.06 } },
};

const item = {
  hidden: { opacity: 0, y: 8 },
  show: { opacity: 1, y: 0 },
};

function greeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 18) return "Good afternoon";
  return "Good evening";
}

/**
 * The real product Dashboard (docs/05 §9, ADR-106) - composed
 * client-side from already-existing per-domain endpoints, since
 * `GET /dashboard` is an unimplemented stub. Portfolio Summary/Watchlist
 * widgets are omitted (ADR-106) - the former has no underlying feature
 * anywhere in this project, the latter would just re-embed the
 * Watchlists placeholder (ADR-103) redundantly.
 *
 * Presentation ported from the reference UI (docs/56) - stat cards
 * (portfolio value/P&L/win rate) and the live symbol ticker from that
 * reference are intentionally NOT reproduced here: neither has a backing
 * data model in this app (`Asset` carries no price field, and portfolio/
 * P&L tracking doesn't exist per ADR-106), and inventing fake numbers for
 * them would violate "never invent architecture." The premium visual
 * system (cards, spacing, color, motion) is instead applied to the real
 * six widgets below.
 */
export default function DashboardPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [refreshing, setRefreshing] = useState(false);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await queryClient.invalidateQueries();
    } finally {
      setRefreshing(false);
    }
  }

  return (
    <div>
      <PageContainer>
        <PageHeader
          title={`${greeting()}${user?.full_name ? `, ${user.full_name.split(" ")[0]}` : ""}`}
          description="Your market overview at a glance."
          actions={
            <Button variant="outline" size="sm" disabled={refreshing} onClick={() => void handleRefresh()}>
              <Loader2 className={`mr-2 size-3.5 ${refreshing ? "animate-spin" : ""}`} />
              {refreshing ? "Refreshing…" : "Refresh all"}
            </Button>
          }
        />
        <motion.div
          variants={container}
          initial="hidden"
          animate="show"
          className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3"
        >
          {WIDGETS.map((Widget, index) => (
            <motion.div key={index} variants={item} className={index === 0 ? "lg:col-span-2" : undefined}>
              <Widget />
            </motion.div>
          ))}
        </motion.div>
      </PageContainer>
    </div>
  );
}
