import { beforeEach, describe, expect, it } from "vitest";
import { useAuthStore } from "@/stores/useAuthStore";
import type { UserPublic } from "@/types/api";

const mockUser: UserPublic = {
  id: "user-1",
  username: "testuser",
  email: "test@example.com",
  role: "ml_engineer",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  last_login_at: null,
};

describe("useAuthStore", () => {
  beforeEach(() => {
    useAuthStore.setState({
      accessToken: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
    });
  });

  it("starts unauthenticated with no tokens or user", () => {
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.user).toBeNull();
  });

  it("logIn sets tokens, user, and isAuthenticated", () => {
    useAuthStore.getState().logIn("access-token-123", "refresh-token-456", mockUser);
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe("access-token-123");
    expect(state.refreshToken).toBe("refresh-token-456");
    expect(state.user).toEqual(mockUser);
  });

  it("setTokens updates tokens without touching the user object (silent refresh)", () => {
    useAuthStore.getState().logIn("old-access", "old-refresh", mockUser);
    useAuthStore.getState().setTokens("new-access", "new-refresh");

    const state = useAuthStore.getState();
    expect(state.accessToken).toBe("new-access");
    expect(state.refreshToken).toBe("new-refresh");
    expect(state.user).toEqual(mockUser); // unchanged
    expect(state.isAuthenticated).toBe(true); // unchanged
  });

  it("logOut clears everything back to the unauthenticated state", () => {
    useAuthStore.getState().logIn("access", "refresh", mockUser);
    useAuthStore.getState().logOut();

    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
    expect(state.refreshToken).toBeNull();
    expect(state.user).toBeNull();
  });
});
