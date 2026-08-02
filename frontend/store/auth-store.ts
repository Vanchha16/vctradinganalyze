import { create } from "zustand";

import type { UserResponse } from "@/services/types";

/**
 * "idle": not yet checked. "loading": a session-restore/auth request is
 * in flight. "authenticated"/"unauthenticated": resolved. AuthGuard
 * (components/layout/auth-guard.tsx) renders nothing but a loading state
 * until status leaves "idle"/"loading" - eliminates the flash of
 * protected content or a premature redirect (ADR-099).
 */
export type AuthStatus = "idle" | "loading" | "authenticated" | "unauthenticated";

interface AuthState {
  accessToken: string | null;
  user: UserResponse | null;
  status: AuthStatus;
  setStatus: (status: AuthStatus) => void;
  setSession: (session: { accessToken: string; user: UserResponse }) => void;
  setAccessToken: (accessToken: string) => void;
  clearSession: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  accessToken: null,
  user: null,
  status: "idle",
  setStatus: (status) => set({ status }),
  setSession: ({ accessToken, user }) => set({ accessToken, user, status: "authenticated" }),
  setAccessToken: (accessToken) => set({ accessToken }),
  clearSession: () => set({ accessToken: null, user: null, status: "unauthenticated" }),
}));
