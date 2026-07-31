import type { ReactNode } from "react";

export function PageContainer({ children }: { children: ReactNode }) {
  return <div className="mx-auto w-full max-w-screen-2xl px-4 py-6 sm:px-6 lg:px-8">{children}</div>;
}
