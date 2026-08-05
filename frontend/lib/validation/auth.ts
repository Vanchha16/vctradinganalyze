import { z } from "zod";

// Phase 8E (docs/59 §9) - `registerSchema`/`RegisterFormValues` removed
// alongside the public register page; `lib/validation/admin.ts`'s
// `adminCreateUserSchema` covers the equivalent admin-created-user form.

export const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
