"use client";

import { useEffect, useRef } from "react";

import { getCurrentUser, refreshAccessToken } from "@/services/auth";
import { ApiError } from "@/services/api-client";
import { clearStoredRefreshToken, getStoredRefreshToken, setStoredRefreshToken } from "@/lib/auth/token-storage";
import { useAuthStore } from "@/store/auth-store";

/**
 * Mounted once at the root layout (docs/53 §3, ADR-099). On mount, tries
 * to restore a session from the persisted refresh token; resolves to
 * "authenticated" or "unauthenticated" either way. Renders nothing itself
 * - `AuthGuard` (components/layout/auth-guard.tsx) is what actually gates
 * UI on the resulting status, keeping "restore the session" and "decide
 * what to show while it resolves" as two separate concerns.
 */
export function AuthProvider({ children }: { children: React.ReactNode }) {
  const setStatus = useAuthStore((state) => state.setStatus);
  const setSession = useAuthStore((state) => state.setSession);
  const clearSession = useAuthStore((state) => state.clearSession);
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;

    async function restoreSession() {
      const refreshToken = getStoredRefreshToken();
      if (!refreshToken) {
        setStatus("unauthenticated");
        return;
      }

      setStatus("loading");
      try {
        const tokenResponse = await refreshAccessToken(refreshToken);
        if (tokenResponse.refresh_token) {
          setStoredRefreshToken(tokenResponse.refresh_token);
        }
        useAuthStore.getState().setAccessToken(tokenResponse.access_token);
        const user = await getCurrentUser();
        setSession({ accessToken: tokenResponse.access_token, user });
      } catch (error) {
        if (error instanceof ApiError) {
          clearStoredRefreshToken();
        }
        clearSession();
      }
    }

    void restoreSession();
  }, [setStatus, setSession, clearSession]);

  return <>{children}</>;
}
