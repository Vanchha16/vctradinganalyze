"use client";

import { PageHeader } from "@/components/shared/page-header";
import { Skeleton } from "@/components/ui/skeleton";
import { PageContainer } from "@/features/dashboard/components/page-container";
import { ProfileSummary } from "@/features/profile/components/profile-summary";
import { useAuth } from "@/hooks/use-auth";

export default function ProfilePage() {
  const { user, status } = useAuth();

  return (
    <div>
      <PageHeader title="Profile" description="Your account information." />
      <PageContainer>
        {status !== "authenticated" || !user ? <Skeleton className="h-64 w-full" /> : <ProfileSummary user={user} />}
      </PageContainer>
    </div>
  );
}
