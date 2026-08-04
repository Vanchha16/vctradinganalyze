import { AlertTriangle, CheckCircle2, ShieldAlert, XCircle } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

interface EvidenceGroupConfig {
  icon: typeof CheckCircle2;
  title: string;
  items: string[];
  dot: string;
  text: string;
}

/**
 * Vertical timeline presentation of the four evidence groups (still the
 * same fields, same icons/colors as before) - a connecting rail groups
 * Supporting -> Conflicting -> Risks -> Invalidation into one narrative
 * flow instead of four disconnected cards. Items within a group have no
 * timestamps (they're just strings), so this is a narrative ordering,
 * not a chronological one.
 */
export function EvidenceList({
  supportingEvidence,
  conflictingEvidence,
  risks,
  invalidationConditions,
}: {
  supportingEvidence: string[];
  conflictingEvidence: string[];
  risks: string[];
  invalidationConditions: string[];
}) {
  const groups: EvidenceGroupConfig[] = [
    { icon: CheckCircle2, title: "Supporting Evidence", items: supportingEvidence, dot: "bg-success", text: "text-success" },
    { icon: XCircle, title: "Conflicting Evidence", items: conflictingEvidence, dot: "bg-destructive", text: "text-destructive" },
    { icon: AlertTriangle, title: "Risks", items: risks, dot: "bg-warning", text: "text-warning" },
    {
      icon: ShieldAlert,
      title: "Invalidation Conditions",
      items: invalidationConditions,
      dot: "bg-muted-foreground",
      text: "text-muted-foreground",
    },
  ].filter((group) => group.items.length > 0);

  if (groups.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Evidence</CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="relative flex flex-col gap-8 border-l-2 border-primary/20 pl-6">
          {groups.map((group) => (
            <li key={group.title} className="relative">
              <span
                className={cn(
                  "absolute -left-[1.85rem] top-0.5 h-4 w-4 rounded-full shadow-sm ring-4 ring-background",
                  group.dot,
                )}
                aria-hidden
              />
              <p className={cn("mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide", group.text)}>
                <group.icon className="h-3.5 w-3.5" />
                {group.title}
              </p>
              <ul className="flex flex-col gap-1.5 text-sm">
                {group.items.map((item, index) => (
                  <li key={index} className="text-muted-foreground">
                    • {item}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
