import { z } from "zod";

/**
 * Add/Edit User dialog schemas (Phase 8D). Mirrors `lib/validation/auth.ts`'s
 * shape - the backend (`AdminUserService`/`UserService`) remains the source
 * of truth for uniqueness/policy; this is UX convenience only.
 */

const USER_ROLES = [
  "guest",
  "registered",
  "premium",
  "moderator",
  "support",
  "admin",
  "super_admin",
] as const;

export const adminCreateUserSchema = z.object({
  email: z.email("Enter a valid email address."),
  username: z
    .string()
    .min(3, "Username must be at least 3 characters.")
    .max(50, "Username must be 50 characters or fewer."),
  full_name: z.string().optional(),
  role: z.enum(USER_ROLES),
  password: z
    .string()
    .min(12, "Password must be at least 12 characters.")
    .optional()
    .or(z.literal("")),
});

export type AdminCreateUserFormValues = z.infer<typeof adminCreateUserSchema>;

export const adminEditUserSchema = z.object({
  email: z.email("Enter a valid email address."),
  username: z
    .string()
    .min(3, "Username must be at least 3 characters.")
    .max(50, "Username must be 50 characters or fewer."),
  full_name: z.string().optional(),
});

export type AdminEditUserFormValues = z.infer<typeof adminEditUserSchema>;
