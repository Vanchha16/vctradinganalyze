import { Suspense } from "react";

import { GuestGuard } from "@/components/layout/guest-guard";

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={null}>
      <GuestGuard>{children}</GuestGuard>
    </Suspense>
  );
}
