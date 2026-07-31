import { Suspense } from "react";

import { Sidebar } from "@/features/dashboard/components/sidebar";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      <Suspense fallback={null}>
        <Sidebar />
      </Suspense>
      <main className="flex-1">
        <Suspense fallback={null}>{children}</Suspense>
      </main>
    </div>
  );
}
