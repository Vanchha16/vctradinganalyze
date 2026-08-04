"use client";

import { Laptop, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Laptop },
] as const;

/**
 * The already-existing theme picker (`components/shared/theme-toggle.tsx`,
 * Phase 7A), relocated into a dedicated Settings section in addition to
 * its `UserMenu` quick-access entry (ADR-104).
 */
export function AppearanceSection() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Appearance</CardTitle>
      </CardHeader>
      <CardContent className="flex gap-3">
        {OPTIONS.map(({ value, label, icon: Icon }) => (
          <Button
            key={value}
            variant="outline"
            className={cn(
              "flex h-auto flex-col items-center gap-2 px-6 py-4",
              mounted && theme === value ? "border-primary text-primary" : undefined,
            )}
            onClick={() => setTheme(value)}
          >
            <Icon className="h-5 w-5" />
            <span className="text-xs">{label}</span>
          </Button>
        ))}
      </CardContent>
    </Card>
  );
}
