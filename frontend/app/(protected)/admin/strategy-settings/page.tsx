"use client";

import { SlidersHorizontal } from "lucide-react";

import { EmptyState } from "@/components/shared/empty-state";
import { PageHeader } from "@/components/shared/page-header";
import { Panel } from "@/components/shared/premium";
import { Skeleton } from "@/components/ui/skeleton";
import { RuntimeSettingsForm } from "@/features/admin/components/runtime-settings-form";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { useAuth } from "@/hooks/use-auth";
import { useRuntimeSettings } from "@/hooks/use-runtime-settings";

/**
 * ADR-178 - strategy and signal settings, changed at runtime instead of
 * by editing `.env` on the server and restarting. Super admin only, the same
 * boundary as EA tokens (ADR-161); the backend enforces it, this page only
 * explains instead of showing a 403.
 */
export default function StrategySettingsPage() {
  const { user, status } = useAuth();
  const isSuperAdmin = user?.role === "super_admin";
  const query = useRuntimeSettings(isSuperAdmin);

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="Strategy Settings"
          description="Turn strategies on or off, set tight stop/target distances, and control how signals are confirmed - without touching the server."
        />
        {status !== "authenticated" || (isSuperAdmin && query.isLoading) ? (
          <Skeleton className="h-96 w-full" />
        ) : !isSuperAdmin ? (
          <Panel>
            <EmptyState
              icon={SlidersHorizontal}
              title="Super admin only"
              description="These settings change what the EA trades, so only the account owner can see or change them."
            />
          </Panel>
        ) : query.isError ? (
          <ErrorCard error={query.error} onRetry={() => query.refetch()} />
        ) : query.data ? (
          <RuntimeSettingsForm data={query.data} />
        ) : null}
      </PageContainer>
    </div>
  );
}
