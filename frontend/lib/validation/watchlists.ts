import { z } from "zod";

/**
 * Create/Rename Watchlist dialog schema (Phase 7D-B). The backend
 * (`WatchlistCreateRequest`/`WatchlistRenameRequest`, `min_length=1,
 * max_length=255`) remains the source of truth; this is UX convenience
 * only, mirrors `lib/validation/admin.ts`'s shape.
 */
export const watchlistNameSchema = z.object({
  name: z
    .string()
    .min(1, "Name is required.")
    .max(255, "Name must be 255 characters or fewer."),
});

export type WatchlistNameFormValues = z.infer<typeof watchlistNameSchema>;
