"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { AccountSection } from "@/features/settings/components/account-section";
import { AppearanceSection } from "@/features/settings/components/appearance-section";
import { TelegramSection } from "@/features/settings/components/telegram-section";
import { useAuth } from "@/hooks/use-auth";

export default function SettingsPage() {
  const { user, status } = useAuth();

  return (
    <div>
      <PageHeader title="Settings" description="Manage your appearance and account." />
      <PageContainer>
        <div className="flex flex-col gap-6">
          <AppearanceSection />
          <TelegramSection />
          {status !== "authenticated" || !user ? <Skeleton className="h-48 w-full" /> : <AccountSection user={user} />}
        </div>
      </PageContainer>
    </div>
  );
}
