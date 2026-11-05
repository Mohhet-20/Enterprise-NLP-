import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { LoginRequest, TokenResponse } from "@/types/api";

export function useLogin() {
  return useMutation({
    mutationFn: (request: LoginRequest) =>
      apiRequest<TokenResponse>("/auth/login", { method: "POST", body: request, auth: false }),
  });
}

/** Public demo: sign in as the shared guest account (the API answers 404 unless guest access is enabled). */
export function useGuestSession() {
  return useMutation({
    mutationFn: () => apiRequest<TokenResponse>("/auth/guest", { method: "POST", auth: false }),
  });
}
