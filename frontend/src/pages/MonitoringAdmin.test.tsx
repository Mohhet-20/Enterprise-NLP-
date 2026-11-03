import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MonitoringPage } from "@/pages/MonitoringPage";
import { AdminPage } from "@/pages/AdminPage";
import { useAuthStore } from "@/stores/useAuthStore";
import { apiRequest } from "@/lib/api";
import type { UserRole } from "@/types/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, apiRequest: vi.fn() };
});

function renderPage(page: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{page}</MemoryRouter>
    </QueryClientProvider>
  );
}

function signInAs(role: UserRole) {
  useAuthStore.setState({
    isAuthenticated: true,
    accessToken: "token",
    refreshToken: "refresh",
    user: { id: "u1", username: "pat", email: "pat@example.com", role, is_active: true, created_at: new Date().toISOString(), last_login_at: null },
  });
}

describe("MonitoringPage", () => {
  beforeEach(() => vi.mocked(apiRequest).mockReset());

  it("aggregates live per-model metrics into request-weighted KPIs", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string) => {
      if (path === "/metrics")
        return {
          "sentiment_analysis:distilbert-sst2": { count: 3, error_rate: 0, avg_latency_ms: 10 },
          "ner:bert-base-ner": { count: 1, error_rate: 1, avg_latency_ms: 50 },
        };
      if (path === "/system") return { status: "ok", cpu_percent: 12, memory_percent: 40, disk_percent: 55 };
      return { status: "ok", checks: { database: { status: "ok" } } };
    });
    signInAs("viewer");
    renderPage(<MonitoringPage />);

    expect(await screen.findByText("4")).toBeInTheDocument();
    expect(screen.getByText("20.0 ms")).toBeInTheDocument(); // (3*10 + 1*50) / 4
    expect(screen.getByText("25.00%", { selector: "p" })).toBeInTheDocument(); // (3*0 + 1*1) / 4
    expect(screen.getByText("distilbert-sst2")).toBeInTheDocument();
    expect(screen.getByRole("meter", { name: "Memory" })).toHaveAttribute("aria-valuenow", "40");
  });

  it("says plainly when no traffic has been recorded", async () => {
    vi.mocked(apiRequest).mockImplementation(async (path: string) =>
      path === "/metrics" ? {} : path === "/system" ? { status: "unavailable", detail: "psutil is not installed." } : { status: "ok", checks: {} }
    );
    signInAs("viewer");
    renderPage(<MonitoringPage />);

    expect(await screen.findByText(/No traffic recorded since the API started/)).toBeInTheDocument();
    expect(await screen.findByText("psutil is not installed.")).toBeInTheDocument();
  });
});

describe("AdminPage", () => {
  beforeEach(() => vi.mocked(apiRequest).mockReset());

  it("blocks roles without audit:read and never calls the API", () => {
    signInAs("data_scientist");
    renderPage(<AdminPage />);

    expect(screen.getByText("No audit access")).toBeInTheDocument();
    expect(apiRequest).not.toHaveBeenCalled();
  });

  it("lists audit entries for an auditor", async () => {
    vi.mocked(apiRequest).mockResolvedValue([
      {
        id: "a1",
        actor_id: "u2",
        actor_username: "alice",
        action: "model.promote",
        resource_type: "model",
        resource_id: "0123456789abcdef",
        details: { stage: "production" },
        ip_address: "10.0.0.5",
        created_at: "2026-10-24T10:00:00Z",
      },
    ]);
    signInAs("auditor");
    renderPage(<AdminPage />);

    expect(await screen.findByText("model.promote")).toBeInTheDocument();
    expect(screen.getByText("alice")).toBeInTheDocument();
    expect(screen.getByText("model/01234567")).toBeInTheDocument();
    expect(screen.getByText("stage=production")).toBeInTheDocument();
    expect(vi.mocked(apiRequest).mock.calls[0]?.[0]).toBe("/audit-logs?limit=100");
  });
});
