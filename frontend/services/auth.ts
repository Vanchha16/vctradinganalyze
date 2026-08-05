import { apiGet, apiPost } from "@/services/api-client";
import type { LoginRequest, TokenResponse, UserResponse } from "@/services/types";

// Phase 8E (docs/59 §9) - public registration removed, POST /auth/register
// returns 403. No `register()` wrapper here anymore - admin account
// creation goes through `services/admin.ts`'s `createAdminUser` instead.

export function login(payload: LoginRequest): Promise<TokenResponse> {
  return apiPost<TokenResponse>("/auth/login", payload);
}

export function refreshAccessToken(refreshToken: string): Promise<TokenResponse> {
  return apiPost<TokenResponse>("/auth/refresh", { refresh_token: refreshToken });
}

export function logout(refreshToken: string): Promise<void> {
  return apiPost<void>("/auth/logout", { refresh_token: refreshToken });
}

export function getCurrentUser(): Promise<UserResponse> {
  return apiGet<UserResponse>("/auth/me");
}
