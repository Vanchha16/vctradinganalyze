"use client";

import Link from "next/link";
import { Search } from "lucide-react";
import { useEffect, useState } from "react";

import { FLAT_NAV } from "@/components/layout/nav-config";

export function CommandPalette({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [q, setQ] = useState("");
  const results = FLAT_NAV.filter((i) => i.label.toLowerCase().includes(q.toLowerCase()));

  useEffect(() => {
    if (!open) setQ("");
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="animate-rise fixed inset-0 z-50 flex items-start justify-center bg-background/70 px-4 pt-[14vh] backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="glass animate-rise w-full max-w-xl overflow-hidden rounded-2xl border border-border shadow-lift"
      >
        <div className="flex items-center gap-3 border-b border-border px-4 py-3.5">
          <Search className="size-4 text-muted-foreground" />
          <input
            autoFocus
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search screens…"
            className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="rounded border border-border px-1.5 py-0.5 text-[10px] text-muted-foreground">ESC</kbd>
        </div>
        <div className="max-h-80 overflow-y-auto p-2">
          {results.length === 0 && <p className="px-3 py-8 text-center text-xs text-muted-foreground">No matches for &ldquo;{q}&rdquo;</p>}
          {results.map((r) => (
            <Link
              key={r.href}
              href={r.href}
              onClick={onClose}
              className="focus-ring flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-surface hover:text-foreground"
            >
              <r.icon className="size-4" />
              {r.label}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
