"use client";

import { useMutation } from "@tanstack/react-query";

import { bookmarkSignal, deleteBookmark } from "@/services/signals";

/**
 * No `GET /signals/bookmark*` list endpoint exists on the backend (only
 * create/delete) - so "is this signal bookmarked" cannot be known on
 * page load/reload. `BookmarkButton` (features/signals) only tracks
 * bookmark state for the current component lifetime, honestly reflecting
 * this gap rather than faking persistence via `localStorage`.
 */
export function useBookmarkSignal() {
  return useMutation({ mutationFn: (signalId: string) => bookmarkSignal(signalId) });
}

export function useDeleteBookmark() {
  return useMutation({ mutationFn: (bookmarkId: string) => deleteBookmark(bookmarkId) });
}
