"use client";

import { Bookmark, BookmarkCheck } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { useBookmarkSignal, useDeleteBookmark } from "@/hooks/use-signal-bookmark";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";

/**
 * No `GET /signals/bookmark*` list endpoint exists - bookmark state is
 * session-local only (component state), not restored on reload
 * (hooks/use-signal-bookmark.ts).
 */
export function BookmarkButton({ signalId }: { signalId: string }) {
  const [bookmarkId, setBookmarkId] = useState<string | null>(null);
  const bookmark = useBookmarkSignal();
  const removeBookmark = useDeleteBookmark();

  async function handleClick() {
    try {
      if (bookmarkId) {
        await removeBookmark.mutateAsync(bookmarkId);
        setBookmarkId(null);
        toast.success("Bookmark removed.");
      } else {
        const result = await bookmark.mutateAsync(signalId);
        setBookmarkId(result.id);
        toast.success("Signal bookmarked.");
      }
    } catch (error) {
      const message = error instanceof ApiError ? error.message : "Something went wrong.";
      toast.error(message);
    }
  }

  return (
    <Button
      variant="ghost"
      className="w-10 px-0"
      onClick={() => void handleClick()}
      disabled={bookmark.isPending || removeBookmark.isPending}
      aria-label={bookmarkId ? "Remove bookmark" : "Bookmark signal"}
    >
      {bookmarkId ? <BookmarkCheck className="h-4 w-4" /> : <Bookmark className="h-4 w-4" />}
    </Button>
  );
}
