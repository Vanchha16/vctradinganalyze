"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

export function RawResponsePanel({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false);

  return (
    <Collapsible open={open} onOpenChange={setOpen} className="rounded-md border border-border">
      <CollapsibleTrigger className="flex w-full items-center justify-between px-3 py-2 text-xs font-medium text-muted-foreground">
        Raw API Response
        <ChevronDown className={`h-4 w-4 transition-transform ${open ? "rotate-180" : ""}`} />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap break-all bg-secondary p-3 text-xs">
          {JSON.stringify(data, null, 2)}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  );
}
