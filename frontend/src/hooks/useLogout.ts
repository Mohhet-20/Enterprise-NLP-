import { useMutation } from "@tanstack/react-query";
import { apiRequest } from "@/lib/api";
import { useAuthStore } from "@/stores/useAuthStore";
import type { LogoutRequest } from "@/types/api";

export function useLogout() {
  const refreshToken = useAuthStore((s) => s.refreshToken);
  const logOut = useAuthStore((s) => s.logOut);

  return useMutation({
    mutationFn: async () => {
      if (refreshToken) {
        await apiRequest<void>("/auth/logout", {
          method: "POST",
          body: { refresh_token: refreshToken } as LogoutRequest,
          auth: false,
        });
      }
    },
    // Clear local session regardless of whether the server call succeeds —
    // an unreachable backend shouldn't be able to trap someone in a
    // "logged in" state on their own device.
    onSettled: () => logOut(),
  });
}
