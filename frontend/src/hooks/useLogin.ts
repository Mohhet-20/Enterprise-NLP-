import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { LoginRequest, TokenResponse } from "@/types/api";

export function useLogin() {
  return useMutation({
    mutationFn: (request: LoginRequest) =>
      apiRequest<TokenResponse>("/auth/login", { method: "POST", body: request, auth: false }),
  });
}
