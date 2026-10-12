import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserPublic } from "@/types/api";

interface AuthState {
  accessToken: string | null;
  refreshToken: string | null;
  user: UserPublic | null;
  isAuthenticated: boolean;
  logIn: (accessToken: string, refreshToken: string, user: UserPublic) => void;
  setTokens: (accessToken: string, refreshToken: string) => void;
  logOut: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      logIn: (accessToken, refreshToken, user) =>
        set({ accessToken, refreshToken, user, isAuthenticated: true }),
      // Used after a silent token refresh — keeps the existing user object.
      setTokens: (accessToken, refreshToken) => set({ accessToken, refreshToken }),
      logOut: () =>
        set({ accessToken: null, refreshToken: null, user: null, isAuthenticated: false }),
    }),
    { name: "nlp-platform-auth" }
  )
);
