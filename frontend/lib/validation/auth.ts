import { z } from "zod";

/**
 * Mirrors the backend's password policy (docs/23_AUTHENTICATION_AND_RBAC.md
 * §7: 12+ chars, upper, lower, number, special character) - a UX
 * convenience only. The backend (`UserService`) remains the source of
 * truth; a submission that somehow passes this client-side check but
 * fails the backend's still surfaces the real `WeakPasswordException`
 * message via `ApiError`.
 */
const passwordSchema = z
  .string()
  .min(12, "Password must be at least 12 characters.")
  .regex(/[a-z]/, "Password must include a lowercase letter.")
  .regex(/[A-Z]/, "Password must include an uppercase letter.")
  .regex(/[0-9]/, "Password must include a number.")
  .regex(/[^A-Za-z0-9]/, "Password must include a special character.");

export const loginSchema = z.object({
  email: z.email("Enter a valid email address."),
  password: z.string().min(1, "Password is required."),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z.object({
  email: z.email("Enter a valid email address."),
  username: z
    .string()
    .min(3, "Username must be at least 3 characters.")
    .max(50, "Username must be 50 characters or fewer."),
  password: passwordSchema,
  full_name: z.string().optional(),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;
