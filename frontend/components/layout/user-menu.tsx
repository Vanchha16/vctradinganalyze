"use client";

import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuth } from "@/hooks/use-auth";
import { toast } from "@/lib/toast";
import { ApiError } from "@/services/api-client";

function initials(value: string): string {
  return value.slice(0, 2).toUpperCase();
}

export function UserMenu() {
  const { user, logout } = useAuth();
  const router = useRouter();

  if (!user) return null;

  async function handleLogout() {
    try {
      await logout();
    } catch (error) {
      // Logout is idempotent server-side (docs/37 §5) - even if the
      // network call fails, the local session is already cleared by
      // useAuth().logout()'s `finally` block, so we still redirect.
      if (error instanceof ApiError) {
        toast.error(error.message);
      }
    } finally {
      router.replace("/login");
    }
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="sm"
          className="gap-2 rounded-lg border-border bg-surface py-1 pl-1 pr-2.5 hover:bg-surface-2"
          aria-label={`Account menu for ${user.username}`}
        >
          <Avatar className="size-6">
            <AvatarFallback className="bg-gradient-brand text-[10px] font-bold text-primary-foreground">
              {initials(user.username)}
            </AvatarFallback>
          </Avatar>
          <span className="hidden text-[11px] font-medium sm:inline">{user.username}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="flex flex-col">
          <span className="text-sm font-medium">{user.full_name ?? user.username}</span>
          <span className="text-xs font-normal text-muted-foreground">{user.email}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem onClick={() => void handleLogout()}>
          <LogOut className="mr-2 h-4 w-4" />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
