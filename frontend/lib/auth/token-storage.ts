/**
 * The refresh token is the only piece of session state that survives a
 * page reload (ADR-099) - the access token lives in memory only (see
 * auth-store.ts). SSR-safe: every function is a no-op on the server.
 */
const REFRESH_TOKEN_KEY = "claudetrading.refresh_token";

export function getStoredRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function setStoredRefreshToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(REFRESH_TOKEN_KEY, token);
}

export function clearStoredRefreshToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}
