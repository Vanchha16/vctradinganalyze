"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useState } from "react";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Form, FormControl, FormField, FormItem, FormLabel, FormMessage } from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TemporaryPasswordReveal } from "@/features/admin/components/temporary-password-reveal";
import { useCreateAdminUser } from "@/hooks/use-admin-user-actions";
import { formatEnumLabel } from "@/lib/format";
import { toast } from "@/lib/toast";
import { adminCreateUserSchema, type AdminCreateUserFormValues } from "@/lib/validation/admin";
import { ApiError } from "@/services/api-client";
import type { UserRole } from "@/services/types";

/** Only a Super Admin may grant an admin-tier role (docs/59 §6.2/§11,
 * ADR-121) - a plain Admin creating a user only ever sees the non-admin
 * tiers, matching what the backend will actually accept from them. */
const ADMIN_TIER_ROLES: UserRole[] = ["admin", "super_admin"];
const ALL_ROLES: UserRole[] = [
  "guest",
  "registered",
  "premium",
  "moderator",
  "support",
  "admin",
  "super_admin",
];

export function AddUserDialog({
  open,
  onOpenChange,
  actorIsSuperAdmin,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  actorIsSuperAdmin: boolean;
}) {
  const createUser = useCreateAdminUser();
  const [temporaryPassword, setTemporaryPassword] = useState<string | null>(null);
  const [createdUsername, setCreatedUsername] = useState<string | null>(null);

  const availableRoles = actorIsSuperAdmin
    ? ALL_ROLES
    : ALL_ROLES.filter((role) => !ADMIN_TIER_ROLES.includes(role));

  const form = useForm<AdminCreateUserFormValues>({
    resolver: zodResolver(adminCreateUserSchema),
    defaultValues: { email: "", username: "", full_name: "", role: "registered", password: "" },
  });

  function handleClose(next: boolean) {
    if (!next) {
      form.reset();
      setTemporaryPassword(null);
      setCreatedUsername(null);
    }
    onOpenChange(next);
  }

  async function onSubmit(values: AdminCreateUserFormValues) {
    try {
      const result = await createUser.mutateAsync({
        email: values.email,
        username: values.username,
        full_name: values.full_name || undefined,
        role: values.role as UserRole,
        password: values.password || undefined,
      });
      setCreatedUsername(result.username);
      if (result.temporary_password) {
        setTemporaryPassword(result.temporary_password);
      } else {
        toast.success(`${result.username} was created.`);
        handleClose(false);
      }
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to create user.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent>
        {temporaryPassword ? (
          <>
            <DialogHeader>
              <DialogTitle>User created</DialogTitle>
              <DialogDescription>{createdUsername} has been created successfully.</DialogDescription>
            </DialogHeader>
            <TemporaryPasswordReveal password={temporaryPassword} />
            <DialogFooter>
              <Button onClick={() => handleClose(false)}>Done</Button>
            </DialogFooter>
          </>
        ) : (
          <>
            <DialogHeader>
              <DialogTitle>Add user</DialogTitle>
              <DialogDescription>
                Create a new account. Leave password blank to generate a secure temporary one.
              </DialogDescription>
            </DialogHeader>
            <Form {...form}>
              <form onSubmit={form.handleSubmit(onSubmit)} className="flex flex-col gap-4">
                <FormField
                  control={form.control}
                  name="email"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Email</FormLabel>
                      <FormControl>
                        <Input type="email" autoComplete="off" placeholder="trader@example.com" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="username"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Username</FormLabel>
                      <FormControl>
                        <Input autoComplete="off" placeholder="trader" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="full_name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Full name (optional)</FormLabel>
                      <FormControl>
                        <Input autoComplete="off" placeholder="Jane Trader" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="role"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Role</FormLabel>
                      <Select value={field.value} onValueChange={field.onChange}>
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          {availableRoles.map((role) => (
                            <SelectItem key={role} value={role}>
                              {formatEnumLabel(role)}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      {!actorIsSuperAdmin ? (
                        <p className="text-[11px] text-muted-foreground">
                          Only a Super Admin can create Admin-tier accounts.
                        </p>
                      ) : null}
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="password"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Password (optional)</FormLabel>
                      <FormControl>
                        <Input type="password" autoComplete="new-password" placeholder="Leave blank to auto-generate" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => handleClose(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={form.formState.isSubmitting}>
                    {form.formState.isSubmitting ? "Creating..." : "Create user"}
                  </Button>
                </DialogFooter>
              </form>
            </Form>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
