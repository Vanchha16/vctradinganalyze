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

export async function apiGet<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
  const url = new URL(`${API_BASE_URL}${path}`);
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) url.searchParams.set(key, value);
    }
  }

  const response = await fetch(url.toString());
  const body: unknown = await response.json().catch(() => null);

  if (!response.ok) {
    const errorBody = body as { error?: string; message?: string } | null;
    throw new ApiError(
      errorBody?.message ?? "Request failed",
      errorBody?.error ?? "unknown_error",
      response.status,
    );
  }

  return body as T;
}
