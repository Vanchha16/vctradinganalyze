"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useEffect } from "react";
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
import { useUpdateAdminUser } from "@/hooks/use-admin-user-actions";
import { toast } from "@/lib/toast";
import { adminEditUserSchema, type AdminEditUserFormValues } from "@/lib/validation/admin";
import { ApiError } from "@/services/api-client";
import type { AdminUserResponse } from "@/services/types";

/** `role`/`is_active`/`password` are deliberately absent from this form -
 * they have their own single-purpose dialogs/endpoints (docs/59 §6.2/§11
 * "mass assignment"). */
export function EditUserDialog({
  user,
  open,
  onOpenChange,
}: {
  user: AdminUserResponse | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const updateUser = useUpdateAdminUser();

  const form = useForm<AdminEditUserFormValues>({
    resolver: zodResolver(adminEditUserSchema),
    defaultValues: { email: "", username: "", full_name: "" },
  });

  useEffect(() => {
    if (user) {
      form.reset({ email: user.email, username: user.username, full_name: user.full_name ?? "" });
    }
  }, [user, form]);

  async function onSubmit(values: AdminEditUserFormValues) {
    if (!user) return;
    try {
      await updateUser.mutateAsync({
        id: user.id,
        payload: {
          email: values.email,
          username: values.username,
          full_name: values.full_name || undefined,
        },
      });
      toast.success("User updated.");
      onOpenChange(false);
    } catch (error) {
      toast.error(error instanceof ApiError ? error.message : "Failed to update user.");
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit user</DialogTitle>
          <DialogDescription>Update {user?.username}&rsquo;s profile details.</DialogDescription>
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
                    <Input type="email" {...field} />
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
                    <Input {...field} />
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
                  <FormLabel>Full name</FormLabel>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={form.formState.isSubmitting}>
                {form.formState.isSubmitting ? "Saving..." : "Save changes"}
              </Button>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  );
}
