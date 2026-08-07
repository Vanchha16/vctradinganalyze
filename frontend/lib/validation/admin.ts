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

// ---- Admin Assets (Phase 9F, ADR-138) ----

const MARKET_TYPES = ["forex", "metal", "crypto", "index"] as const;

export const adminCreateAssetSchema = z.object({
  symbol: z
    .string()
    .min(1, "Symbol is required.")
    .max(20, "Symbol must be 20 characters or fewer."),
  name: z.string().min(1, "Name is required.").max(255, "Name must be 255 characters or fewer."),
  market_type: z.enum(MARKET_TYPES),
  exchange: z.string().optional(),
  base_currency: z.string().optional(),
  quote_currency: z.string().optional(),
});

export type AdminCreateAssetFormValues = z.infer<typeof adminCreateAssetSchema>;

/** No `symbol` field - it is immutable after creation (ADR-138), so the
 * edit form never offers one to change, mirroring `adminEditUserSchema`
 * excluding `role`/`is_active`/`password`. */
export const adminEditAssetSchema = z.object({
  name: z.string().min(1, "Name is required.").max(255, "Name must be 255 characters or fewer."),
  market_type: z.enum(MARKET_TYPES),
  exchange: z.string().optional(),
  base_currency: z.string().optional(),
  quote_currency: z.string().optional(),
});

export type AdminEditAssetFormValues = z.infer<typeof adminEditAssetSchema>;
