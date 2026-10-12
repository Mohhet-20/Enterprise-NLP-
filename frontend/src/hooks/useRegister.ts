import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import type { RegisterRequest, UserPublic } from "@/types/api";

export function useRegister() {
  return useMutation({
    mutationFn: (request: RegisterRequest) =>
      apiRequest<UserPublic>("/auth/register", { method: "POST", body: request, auth: false }),
  });
}
