import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { useAuthStore } from "@/stores/useAuthStore";

// Renders the real router, app shell, sidebar and top nav together. Unit
// tests of individual components can't catch provider/context wiring bugs
// (e.g. a Tooltip rendered outside its TooltipProvider crashes the whole
// shell after login), so these tests mount everything a signed-in user sees.

function fakeApi(url: string): unknown {
  if (url.endsWith("/tasks")) return { tasks: [] };
  if (url.includes("/status") || url.includes("/health")) return { status: "ok", checks: {} };
  return []; // list endpoints: datasets, models, evaluation runs
}

async function renderAt(path: string) {
  window.history.pushState({}, "", path);
  // The router reads window.location when its module is evaluated.
  vi.resetModules();
  const { default: App } = await import("@/App");
  render(<App />);
}

describe("App shell", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: string | URL | Request) =>
        new Response(JSON.stringify(fakeApi(String(input))), { status: 200 }),
      ),
    );
    useAuthStore.setState({
      isAuthenticated: true,
      accessToken: "token",
      refreshToken: "refresh",
      user: {
        id: "u1",
        username: "admin",
        email: "admin@example.com",
        role: "admin",
        is_active: true,
        created_at: new Date().toISOString(),
        last_login_at: null,
      },
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the playground inside the full shell for a signed-in user", async () => {
    await renderAt("/playground");
    expect(await screen.findByRole("heading", { name: "Inference Playground" })).toBeInTheDocument();
    expect(screen.getByLabelText(/collapse sidebar/i)).toBeInTheDocument();
  });

  it("renders the evaluations page", async () => {
    await renderAt("/evaluations");
    expect(await screen.findByRole("heading", { name: /Evaluation & Error Analysis/ })).toBeInTheDocument();
  });
});
