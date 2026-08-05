"use client";

import { useCallback } from "react";

import { clearStoredRefreshToken, getStoredRefreshToken, setStoredRefreshToken } from "@/lib/auth/token-storage";
import * as authService from "@/services/auth";
import type { LoginRequest } from "@/services/types";
import { useAuthStore } from "@/store/auth-store";

/**
 * The single entry point components use for authentication (docs/53 §3).
 * Wraps `services/auth.ts` + `store/auth-store.ts` so no component talks
 * to either directly - mirrors `hooks/use-assets.ts`'s thin-wrapper-over-
 * a-service pattern.
 */
export function useAuth() {
  const user = useAuthStore((state) => state.user);
  const status = useAuthStore((state) => state.status);
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);

  const login = useCallback(
    async (payload: LoginRequest) => {
      const tokenResponse = await authService.login(payload);
      if (tokenResponse.refresh_token) {
        setStoredRefreshToken(tokenResponse.refresh_token);
      }
      useAuthStore.getState().setAccessToken(tokenResponse.access_token);
      const currentUser = await authService.getCurrentUser();
      setSession({ accessToken: tokenResponse.access_token, user: currentUser });
      return currentUser;
    },
    [setSession],
  );

  const logout = useCallback(async () => {
    const refreshToken = getStoredRefreshToken();
    try {
      if (refreshToken) {
        await authService.logout(refreshToken);
      }
    } finally {
      clearStoredRefreshToken();
      clearSession();
    }
  }, [clearSession]);

  return { user, status, login, logout };
}
