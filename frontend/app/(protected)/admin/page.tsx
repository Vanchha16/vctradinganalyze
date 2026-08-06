"use client";

import { Activity, ShieldAlert, ShieldCheck, UserCheck, UserX, Users as UsersIcon } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { StatCard } from "@/features/admin/components/stat-card";
import { useAdminSystemStatus } from "@/hooks/use-admin-system-status";
import { useAdminUsers } from "@/hooks/use-admin-users";
import { systemStatusVariant, userRoleVariant, userStatusVariant } from "@/lib/badge-variants";
import { formatDateTime, formatEnumLabel } from "@/lib/format";

/**
 * Composed client-side from real `GET /admin/users`/`GET /admin/system`
 * calls with different filters - same "no new backend endpoint" pattern
 * Phase 7B's product Dashboard established for `/dashboard` (ADR-106). No
 * fabricated numbers: every stat here is a real, currently-derivable count.
 */
export default function AdminDashboardPage() {
  const totalQuery = useAdminUsers({ limit: 1 });
  const activeQuery = useAdminUsers({ is_active: "true", limit: 1 });
  const disabledQuery = useAdminUsers({ is_active: "false", limit: 1 });
  const adminQuery = useAdminUsers({ role: "admin", limit: 1 });
  const superAdminQuery = useAdminUsers({ role: "super_admin", limit: 1 });
  const recentQuery = useAdminUsers({ limit: 8 });
  const systemQuery = useAdminSystemStatus();

  return (
    <div>
      <PageContainer>
        <PageHeader title="Admin Dashboard" description="Platform-wide account overview." />

        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-5">
          <StatCard label="Total Users" value={totalQuery.data?.total} icon={UsersIcon} isLoading={totalQuery.isLoading} />
          <StatCard label="Active" value={activeQuery.data?.total} icon={UserCheck} isLoading={activeQuery.isLoading} />
          <StatCard label="Disabled" value={disabledQuery.data?.total} icon={UserX} isLoading={disabledQuery.isLoading} />
          <StatCard label="Admins" value={adminQuery.data?.total} icon={ShieldCheck} isLoading={adminQuery.isLoading} />
          <StatCard label="Super Admins" value={superAdminQuery.data?.total} icon={ShieldAlert} isLoading={superAdminQuery.isLoading} />
        </div>

        <div className="mt-4">
          <Panel>
            <PanelHeader
              title="System status"
              subtitle="Liveness and today's activity"
              icon={<Activity className="size-4" />}
            />
            <div className="flex flex-col gap-3 p-4">
              {systemQuery.isLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : systemQuery.data ? (
                <>
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={systemStatusVariant(systemQuery.data.database)}>
                      Database: {formatEnumLabel(systemQuery.data.database)}
                    </Badge>
                    <Badge variant={systemStatusVariant(systemQuery.data.redis)}>
                      Redis: {formatEnumLabel(systemQuery.data.redis)}
                    </Badge>
                    <span className="text-[11px] text-muted-foreground">
                      {systemQuery.data.signals_today} signal{systemQuery.data.signals_today === 1 ? "" : "s"} today ·{" "}
                      {systemQuery.data.ai_analyses_today} AI{" "}
                      {systemQuery.data.ai_analyses_today === 1 ? "analysis" : "analyses"} today
                    </span>
                  </div>
                  <Link href="/admin/system-health" className="text-[11px] text-primary hover:underline">
                    View System Health →
                  </Link>
                </>
              ) : (
                <p className="text-[11px] text-muted-foreground">System status unavailable.</p>
              )}
            </div>
          </Panel>
        </div>

        <div className="mt-4">
          <Panel>
            <PanelHeader title="Recently created accounts" subtitle="Newest first" />
            {recentQuery.isLoading ? (
              <div className="p-4">
                <Skeleton className="h-64 w-full" />
              </div>
            ) : (
              <div className="divide-y divide-border/70">
                {(recentQuery.data?.items ?? []).map((user) => (
                  <div key={user.id} className="flex items-center justify-between gap-4 px-5 py-3">
                    <div className="min-w-0">
                      <p className="truncate text-[13px] font-medium">{user.full_name || user.username}</p>
                      <p className="truncate text-[11px] text-muted-foreground">{user.email}</p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <Badge variant={userRoleVariant(user.role)}>{formatEnumLabel(user.role)}</Badge>
                      <Badge variant={userStatusVariant(user.is_active)}>
                        {user.is_active ? "Active" : "Disabled"}
                      </Badge>
                      <span className="text-[11px] text-muted-foreground">{formatDateTime(user.created_at)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Panel>
        </div>

        <p className="mt-4 text-center text-[11px] text-muted-foreground">
          Looking for more? <Link href="/admin/users" className="text-primary hover:underline">Manage all users →</Link>
        </p>
      </PageContainer>
    </div>
  );
}
