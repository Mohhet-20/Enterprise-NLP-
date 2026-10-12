import { describe, expect, it, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "@/routes/ProtectedRoute";
import { useAuthStore } from "@/stores/useAuthStore";

function renderWithRoute(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login" element={<div>Login Page</div>} />
        <Route element={<ProtectedRoute />}>
          <Route path="/playground" element={<div>Playground Page</div>} />
        </Route>
      </Routes>
    </MemoryRouter>
  );
}

describe("ProtectedRoute", () => {
  beforeEach(() => {
    useAuthStore.setState({ isAuthenticated: false, user: null, accessToken: null, refreshToken: null });
  });

  it("redirects to /login when not authenticated", () => {
    renderWithRoute("/playground");
    expect(screen.getByText("Login Page")).toBeInTheDocument();
    expect(screen.queryByText("Playground Page")).not.toBeInTheDocument();
  });

  it("renders the protected content when authenticated", () => {
    useAuthStore.setState({ isAuthenticated: true });
    renderWithRoute("/playground");
    expect(screen.getByText("Playground Page")).toBeInTheDocument();
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
  });
});
