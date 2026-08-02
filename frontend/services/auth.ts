import { apiGet, apiPost } from "@/services/api-client";
import type { LoginRequest, RegisterRequest, TokenResponse, UserResponse } from "@/services/types";

export function register(payload: RegisterRequest): Promise<UserResponse> {
  return apiPost<UserResponse>("/auth/register", payload);
}

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
