import Link from "next/link";
import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

import { Badge, type BadgeProps } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface SummaryFact {
  label: string;
  value: ReactNode;
}

export function SummaryCard({
  title,
  href,
  value,
  valueLabel,
  badges,
  facts,
}: {
  title: string;
  href: string;
  value: string;
  valueLabel: string;
  badges: { label: string; variant?: BadgeProps["variant"] }[];
  facts: SummaryFact[];
}) {
  return (
    <Card className="flex flex-col">
      <CardHeader className="space-y-0 pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle>{title}</CardTitle>
          <Link
            href={href}
            className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            View details
            <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      </CardHeader>
      <CardContent className="flex flex-1 flex-col gap-5">
        <div>
          <p className="text-4xl font-bold tabular-nums leading-none">{value}</p>
          <p className="mt-1.5 text-xs uppercase tracking-wide text-muted-foreground">{valueLabel}</p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {badges.map((badge) => (
            <Badge key={badge.label} variant={badge.variant}>
              {badge.label}
            </Badge>
          ))}
        </div>

        <dl className="mt-auto grid grid-cols-2 gap-3 border-t border-border pt-4 text-sm">
          {facts.map((fact) => (
            <div key={fact.label}>
              <dt className="text-xs text-muted-foreground">{fact.label}</dt>
              <dd className="mt-0.5 font-medium">{fact.value}</dd>
            </div>
          ))}
        </dl>
      </CardContent>
    </Card>
  );
}
