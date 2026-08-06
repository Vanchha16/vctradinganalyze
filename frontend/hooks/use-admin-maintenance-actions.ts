"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ADMIN_SYSTEM_STATUS_QUERY_KEY } from "@/hooks/use-admin-system-status";
import { refreshNews, runAdminMaintenance } from "@/services/admin";
import type { MaintenanceActionResponse, NewsRefreshResponse } from "@/services/types";

/**
 * The backend runs both ingestion pipelines synchronously and inline
 * (docs/58's approved spec, ADR-130's recorded tradeoff) - a real vendor
 * call can take many seconds. Without a client-side timeout, a hung
 * request (dropped connection, vendor never responding) would leave the
 * triggering button disabled forever with no way out. 60s is a generous,
 * hand-picked starting point (same "not empirically calibrated" caveat as
 * every other threshold in this project) - long enough for a normal slow
 * response, short enough that the operator isn't left waiting indefinitely.
 */
const MAINTENANCE_TIMEOUT_MS = 60_000;

export class MaintenanceTimeoutError extends Error {
  constructor() {
    super(
      "The request timed out after 60s. It may still be running in the background - " +
        "check Audit Logs before retrying.",
    );
    this.name = "MaintenanceTimeoutError";
  }
}

function withTimeout<T>(run: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), MAINTENANCE_TIMEOUT_MS);
  return run(controller.signal)
    .catch((error: unknown) => {
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new MaintenanceTimeoutError();
      }
      throw error;
    })
    .finally(() => clearTimeout(timeoutId));
}

/** Uses the dedicated `POST /admin/news` route rather than
 * `POST /admin/maintenance {"action": "refresh_news"}` - both share the
 * identical backend implementation (ADR-130), but the single-purpose
 * route is the more direct call for this specific button. */
export function useRefreshNews() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => withTimeout<NewsRefreshResponse>((signal) => refreshNews(signal)),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ADMIN_SYSTEM_STATUS_QUERY_KEY }),
  });
}

/** No dedicated `POST /admin/calendar` route exists - this is the only
 * way to trigger a calendar refresh (`POST /admin/maintenance
 * {"action": "refresh_calendar"}`). */
export function useRefreshCalendar() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      withTimeout<MaintenanceActionResponse>((signal) =>
        runAdminMaintenance("refresh_calendar", signal),
      ),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ADMIN_SYSTEM_STATUS_QUERY_KEY }),
  });
}
