import { AdminGuard } from "@/components/layout/admin-guard";

/**
 * `AppShell` is already provided by `(protected)/layout.tsx` - this layout
 * only adds the role check on top (docs/59 §5.1). No duplicated shell/sidebar.
 */
export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return <AdminGuard>{children}</AdminGuard>;
}
