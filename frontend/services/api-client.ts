import { clearStoredRefreshToken, getStoredRefreshToken } from "@/lib/auth/token-storage";
import { useAuthStore } from "@/store/auth-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly errorCode: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  params?: Record<string, string | undefined>;
  body?: unknown;
}

function buildUrl(path: string, params?: Record<string, string | undefined>): string {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, value);
    }
  }
  return url.toString();
}

/**
 * A direct fetch to POST /auth/refresh - deliberately not routed through
 * `services/auth.ts`'s `refreshAccessToken` (which itself calls this
 * module's `apiPost`), to avoid a circular import between the two
 * modules. Used only for this module's own silent-retry-on-401 logic
 * (docs/53 §3, ADR-099).
 */
async function refreshAccessTokenOnce(): Promise<string | null> {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });
  if (!response.ok) return null;

  const body = (await response.json().catch(() => null)) as { access_token?: string } | null;
  return body?.access_token ?? null;
}

async function request<T>(
  method: "GET" | "POST" | "DELETE",
  path: string,
  options: RequestOptions = {},
  isRetry = false,
): Promise<T> {
  const { accessToken } = useAuthStore.getState();
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers.Authorization = `Bearer ${accessToken}`;

  const response = await fetch(buildUrl(path, options.params), {
    method,
    headers,
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });

  if (response.status === 204) return undefined as T;

  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = body as { error?: string; message?: string } | null;

    // One silent refresh-and-retry on an expired access token (mirrors
    // ADR-081's "one retry, then fail gracefully" precedent) - only when
    // a token was actually attached, so login/register 401s (wrong
    // credentials) never trigger a pointless refresh attempt.
    if (response.status === 401 && !isRetry && accessToken) {
      const newAccessToken = await refreshAccessTokenOnce();
      if (newAccessToken) {
        useAuthStore.getState().setAccessToken(newAccessToken);
        return request<T>(method, path, options, true);
      }
      clearStoredRefreshToken();
      useAuthStore.getState().clearSession();
    }

    throw new ApiError(
      errorBody?.message ?? "Request failed",
      errorBody?.error ?? "unknown_error",
      response.status,
    );
  }

  return body as T;
}

export function apiGet<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  return request<T>("GET", path, { params });
}

export function apiPost<T>(path: string, body?: unknown): Promise<T> {
  return request<T>("POST", path, { body });
}

export function apiDelete<T = void>(path: string): Promise<T> {
  return request<T>("DELETE", path);
}
