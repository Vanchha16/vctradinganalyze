"use client";

import { motion } from "framer-motion";
import { ArrowUpRight, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatRelativeTime } from "@/lib/format";
import type { WatchlistSummaryResponse } from "@/services/types";

/** Name, item count, quick rename/delete (docs/58 §2.4) - same
 * hover-lift/card shape as `SignalCard`. `item_count` comes straight from
 * the list response; this never calls the detail endpoint per card. */
export function WatchlistCard({
  watchlist,
  onRename,
  onDelete,
}: {
  watchlist: WatchlistSummaryResponse;
  onRename: (watchlist: WatchlistSummaryResponse) => void;
  onDelete: (watchlist: WatchlistSummaryResponse) => void;
}) {
  return (
    <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }}>
      <Card className="transition-shadow hover:shadow-md">
        <CardHeader className="space-y-0 pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="truncate">{watchlist.name}</CardTitle>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="sm"
                className="w-8 shrink-0 px-0"
                aria-label={`Rename ${watchlist.name}`}
                onClick={() => onRename(watchlist)}
              >
                <Pencil className="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="w-8 shrink-0 px-0 text-destructive hover:text-destructive"
                aria-label={`Delete ${watchlist.name}`}
                onClick={() => onDelete(watchlist)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex items-center justify-between gap-3">
            <Badge variant="outline">
              {watchlist.item_count} {watchlist.item_count === 1 ? "asset" : "assets"}
            </Badge>
            <Link
              href={`/watchlists/${watchlist.id}`}
              className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
            >
              Open
              <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <p className="text-xs text-muted-foreground">{formatRelativeTime(watchlist.created_at)}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
