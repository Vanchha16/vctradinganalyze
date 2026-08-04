import { ArrowUpRight } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

import { Panel, PanelHeader } from "@/components/shared/premium";

/**
 * Shared shape for docs/05 §9's Dashboard widgets (Market Overview,
 * Latest Signals, Economic Events, Breaking News, AI Insights, Quick
 * Actions) - title + "view all" link + content, reused across all six
 * instead of redefining the header per widget.
 */
export function WidgetCard({
  title,
  viewAllHref,
  icon,
  children,
}: {
  title: string;
  viewAllHref?: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <Panel className="flex h-full flex-col">
      <PanelHeader
        title={title}
        icon={icon}
        right={
          viewAllHref ? (
            <Link
              href={viewAllHref}
              className="focus-ring flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-surface-2 hover:text-foreground"
            >
              View all
              <ArrowUpRight className="size-3.5" />
            </Link>
          ) : undefined
        }
      />
      <div className="flex flex-1 flex-col gap-3 p-4">{children}</div>
    </Panel>
  );
}
