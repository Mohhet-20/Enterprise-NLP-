import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { LoginPage } from "@/pages/LoginPage";
import { useAuthStore } from "@/stores/useAuthStore";
import { apiRequest } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiRequest: vi.fn() };
});

function renderLoginPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe("LoginPage", () => {
  beforeEach(() => {
    vi.mocked(apiRequest).mockReset();
    useAuthStore.setState({ isAuthenticated: false, user: null, accessToken: null, refreshToken: null });
  });

  it("disables the submit button until both fields are filled", async () => {
    const user = userEvent.setup();
    renderLoginPage();

    const submitButton = screen.getByRole("button", { name: /sign in/i });
    expect(submitButton).toBeDisabled();

    await user.type(screen.getByLabelText(/username/i), "mohhet");
    expect(submitButton).toBeDisabled(); // password still empty

    await user.type(screen.getByLabelText(/^password$/i), "StrongPass123!");
    expect(submitButton).not.toBeDisabled();
  });

  it("submits the trimmed username, password, and remember_me flag", async () => {
    vi.mocked(apiRequest).mockResolvedValue({
      access_token: "access-123",
      refresh_token: "refresh-456",
      token_type: "bearer",
      expires_in: 1800,
      user: {
        id: "user-1",
        username: "mohhet",
        email: "mohhet@example.com",
        role: "ml_engineer",
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
        last_login_at: null,
      },
    });

    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText(/username/i), "  mohhet  ");
    await user.type(screen.getByLabelText(/^password$/i), "StrongPass123!");
    await user.click(screen.getByLabelText(/remember me/i));
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(apiRequest).toHaveBeenCalledWith(
        "/auth/login",
        expect.objectContaining({
          method: "POST",
          body: { username: "mohhet", password: "StrongPass123!", remember_me: true },
        })
      );
    });
  });

  it("logs the user into the auth store on successful sign-in", async () => {
    const mockUser = {
      id: "user-1",
      username: "mohhet",
      email: "mohhet@example.com",
      role: "ml_engineer" as const,
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
      last_login_at: null,
    };
    vi.mocked(apiRequest).mockResolvedValue({
      access_token: "access-123",
      refresh_token: "refresh-456",
      token_type: "bearer",
      expires_in: 1800,
      user: mockUser,
    });

    const user = userEvent.setup();
    renderLoginPage();

    await user.type(screen.getByLabelText(/username/i), "mohhet");
    await user.type(screen.getByLabelText(/^password$/i), "StrongPass123!");
    await user.click(screen.getByRole("button", { name: /sign in/i }));

    await waitFor(() => {
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
      expect(useAuthStore.getState().user).toEqual(mockUser);
    });
  });
});
