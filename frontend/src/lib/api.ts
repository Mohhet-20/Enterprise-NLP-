import type { ApiErrorPayload, RefreshRequest, TokenResponse } from "@/types/api";
import { useAuthStore } from "@/stores/useAuthStore";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  code: string;
  status: number;
  requestId?: string;
  details: Record<string, unknown>;

  constructor(status: number, payload: ApiErrorPayload["error"]) {
    super(payload.message);
    this.name = "ApiError";
    this.code = payload.code;
    this.status = status;
    this.requestId = payload.request_id;
    this.details = payload.details;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  auth?: boolean;
  /** Internal — prevents infinite refresh retry loops. */
  _isRetry?: boolean;
}

async function rawRequest(path: string, options: RequestOptions, accessToken: string | null): Promise<Response> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth && accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

  return fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

async function parseError(response: Response): Promise<ApiError> {
  let payload: ApiErrorPayload | null = null;
  try {
    payload = await response.json();
  } catch {
    // response body wasn't JSON — fall through to the generic error below
  }
  if (payload?.error) return new ApiError(response.status, payload.error);
  return new ApiError(response.status, {
    code: "UnknownError",
    message: `Request failed with status ${response.status}`,
    details: {},
    request_id: "",
  });
}

/**
 * On a 401 from an authenticated request, tries exactly one silent refresh
 * (via the stored refresh token) and retries the original request once.
 * If the refresh itself fails, the session is cleared — the caller sees
 * the original 401 and the UI's route guard sends them to /login.
 */
export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { auth = true, _isRetry = false } = options;
  const { accessToken, refreshToken, setTokens, logOut } = useAuthStore.getState();

  const response = await rawRequest(path, options, accessToken);

  if (response.ok) {
    if (response.status === 204) return undefined as T;
    return response.json() as Promise<T>;
  }

  if (response.status === 401 && auth && !_isRetry && refreshToken) {
    const refreshResponse = await rawRequest(
      "/auth/refresh",
      { method: "POST", body: { refresh_token: refreshToken } as RefreshRequest, auth: false },
      null
    );

    if (refreshResponse.ok) {
      const bundle: TokenResponse = await refreshResponse.json();
      setTokens(bundle.access_token, bundle.refresh_token);
      return apiRequest<T>(path, { ...options, _isRetry: true });
    }

    logOut();
  }

  throw await parseError(response);
}
