"use client";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { formatDateTime, formatEnumLabel } from "@/lib/format";
import type { AdminAuditLogResponse } from "@/services/types";

/** Read-only (docs/59 §11, ADR-129 - no route mutates or deletes a log,
 * so this table has no row actions, unlike `UserTable`). A `null` actor
 * (`user_id` is nullable, `ON DELETE SET NULL`) renders as an honest
 * "System / deleted user" label, never a blank cell. */
export function AuditLogTable({
  logs,
  onFilterByActor,
}: {
  logs: AdminAuditLogResponse[];
  onFilterByActor: (log: AdminAuditLogResponse) => void;
}) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Timestamp</TableHead>
          <TableHead>Actor</TableHead>
          <TableHead>Action</TableHead>
          <TableHead>Resource</TableHead>
          <TableHead>Resource ID</TableHead>
          <TableHead>IP</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {logs.map((log) => (
          <TableRow key={log.id}>
            <TableCell className="whitespace-nowrap text-muted-foreground">
              {formatDateTime(log.created_at)}
            </TableCell>
            <TableCell>
              {log.user_id ? (
                <button
                  type="button"
                  onClick={() => onFilterByActor(log)}
                  className="focus-ring rounded text-left text-[13px] font-medium text-foreground transition-colors hover:text-primary"
                  aria-label={`Filter by ${log.actor_email ?? log.user_id}`}
                >
                  {log.actor_username ?? log.actor_email ?? log.user_id.slice(0, 8)}
                </button>
              ) : (
                <span className="text-muted-foreground">System / deleted user</span>
              )}
            </TableCell>
            <TableCell>
              <Badge variant="outline">{formatEnumLabel(log.action)}</Badge>
            </TableCell>
            <TableCell className="text-muted-foreground">{formatEnumLabel(log.resource)}</TableCell>
            <TableCell className="text-muted-foreground">
              {log.resource_id ? log.resource_id.slice(0, 8) : "—"}
            </TableCell>
            <TableCell className="text-muted-foreground">{log.ip_address ?? "—"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
