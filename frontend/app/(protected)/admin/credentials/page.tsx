"use client";

import { ShieldAlert } from "lucide-react";

import { PageHeader } from "@/components/shared/page-header";
import { Panel, PanelHeader } from "@/components/shared/premium";
import { Skeleton } from "@/components/ui/skeleton";
import { CredentialRow } from "@/features/admin/components/credential-row";
import { ErrorCard } from "@/features/dashboard/components/error-card";
import { PageContainer } from "@/features/dashboard/components/page-container";
import {
  useAdminCredentials,
  useClearApiCredential,
  useSetApiCredential,
} from "@/hooks/use-admin-credentials";

/**
 * API keys, editable without SSH (ADR-156). Super-admin only - the API
 * enforces that; this page would 403 for anyone else.
 *
 * Deliberately shows no key values. The backend has no route that returns
 * one, so there is nothing to reveal even if this page wanted to.
 */
export default function AdminCredentialsPage() {
  const credentialsQuery = useAdminCredentials();
  const setCredential = useSetApiCredential();
  const clearCredential = useClearApiCredential();

  const storageEnabled = credentialsQuery.data?.storage_enabled ?? false;

  return (
    <div>
      <PageContainer>
        <PageHeader
          title="API Keys"
          description="Update the keys this platform uses to reach its providers."
        />

        {credentialsQuery.isLoading ? (
          <Skeleton className="h-72 w-full" />
        ) : credentialsQuery.isError ? (
          <ErrorCard error={credentialsQuery.error} onRetry={() => credentialsQuery.refetch()} />
        ) : (
          <div className="flex flex-col gap-4">
            {!storageEnabled ? <StorageDisabledNotice /> : null}

            <Panel>
              <PanelHeader title="Providers" />
              <div className="px-4">
                {credentialsQuery.data?.items.map((credential) => (
                  <CredentialRow
                    key={credential.name}
                    credential={credential}
                    storageEnabled={storageEnabled}
                    onSave={(name, value) => setCredential.mutateAsync({ name, value })}
                    onClear={(name) => clearCredential.mutateAsync(name)}
                    isSaving={setCredential.isPending || clearCredential.isPending}
                  />
                ))}
              </div>
            </Panel>

            <p className="text-xs leading-relaxed text-muted-foreground">
              Keys are encrypted before they are stored and are never shown again - only the
              last four characters. A saved key takes effect within about 30 seconds, with no
              restart. Clearing a stored key falls it back to the value in the server&apos;s{" "}
              <code>.env</code>, which is not the same as saving an empty one.
            </p>
          </div>
        )}
      </PageContainer>
    </div>
  );
}

/**
 * Without `CREDENTIAL_ENCRYPTION_KEY` there is nothing to encrypt with,
 * so editing is impossible. Saying so up front beats letting the operator
 * paste a key and hit an error on Save.
 */
function StorageDisabledNotice() {
  return (
    <div className="flex items-start gap-3 rounded-md border border-warning/40 bg-warning/10 p-4">
      <ShieldAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden />
      <div className="text-sm">
        <p className="font-medium">Editing is disabled</p>
        <p className="pt-1 text-muted-foreground">
          <code>CREDENTIAL_ENCRYPTION_KEY</code> is not set on the server, so there is no key to
          encrypt credentials with. The values below are whatever the server&apos;s{" "}
          <code>.env</code> provides, and everything works normally - they just cannot be changed
          from here yet.
        </p>
      </div>
    </div>
  );
}
