/**
 * API client — typed fetch wrapper for the RailPredict backend.
 *
 * All requests go through apiRequest() so:
 * - Base URL is pulled from NEXT_PUBLIC_API_URL once
 * - Errors are handled consistently
 * - Auth headers are attached automatically when a token is present
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(`API ${status}: ${detail}`);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token =
    typeof window !== "undefined" ? localStorage.getItem("access_token") : null;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body.detail ?? detail;
    } catch {
      // response body wasn't JSON — keep statusText
    }
    throw new ApiError(response.status, detail);
  }

  // 204 No Content — return empty object
  if (response.status === 204) return {} as T;

  return response.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: string;
  version?: string;
  db?: string;
}

export const health = {
  liveness: () => apiRequest<HealthResponse>("/healthz"),
  readiness: () => apiRequest<HealthResponse>("/readyz"),
};

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: string;
}

export interface UserPublic {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
}

export const auth = {
  login: (email: string, password: string) =>
    apiRequest<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  refresh: (refresh_token: string) =>
    apiRequest<TokenResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  me: () => apiRequest<UserPublic>("/api/v1/auth/me"),
};

// ---------------------------------------------------------------------------
// Phase 1+ — placeholder exports (not yet implemented on the backend)
// ---------------------------------------------------------------------------

// export const trains = { ... }
// export const stations = { ... }
