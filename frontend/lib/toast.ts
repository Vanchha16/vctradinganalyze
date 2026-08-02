import { toast as sonnerToast } from "sonner";

/**
 * The only module allowed to import `sonner` directly - every call site
 * goes through this thin wrapper (mirrors `services/api-client.ts`
 * wrapping `fetch`), so the underlying toast library can be swapped
 * later without touching every caller.
 */
export const toast = {
  success: (message: string) => sonnerToast.success(message),
  error: (message: string) => sonnerToast.error(message),
  info: (message: string) => sonnerToast(message),
};
