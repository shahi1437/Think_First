import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import type { ReactElement } from "react";
import { describe, expect, it, vi } from "vitest";
import { SystemStatusCard } from "@/components/system-status-card";
import type { BackendConnectivityStatus } from "@/lib/api-client";

function renderWithQueryClient(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>{ui}</QueryClientProvider>,
  );
}

describe("SystemStatusCard", () => {
  it("renders connected API and ready PostgreSQL status", async () => {
    const mockStatus: BackendConnectivityStatus = {
      meta: {
        service: "CodeMentor AI API",
        api_version: "v1",
        app_version: "0.1.0",
        environment: "test",
        request_id: "req-test-1234",
      },
      readiness: {
        status: "ok",
        service: "CodeMentor AI API",
        version: "0.1.0",
        database: "ok",
      },
      readinessHttpStatus: 200,
    };

    const fetcher = vi.fn().mockResolvedValue(mockStatus);
    renderWithQueryClient(<SystemStatusCard fetchStatus={fetcher} />);

    expect(
      screen.getByText(/Checking FastAPI backend connectivity/i),
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("API Server Connected")).toBeInTheDocument();
    });

    expect(screen.getByText("CodeMentor AI API")).toBeInTheDocument();
    expect(screen.getByText("req-test-1234")).toBeInTheDocument();
    expect(screen.getByText("PostgreSQL: Ready")).toBeInTheDocument();
  });

  it("renders degraded database status when API is up but Postgres is down", async () => {
    const degradedStatus: BackendConnectivityStatus = {
      meta: {
        service: "CodeMentor AI API",
        api_version: "v1",
        app_version: "0.1.0",
        environment: "development",
        request_id: "req-degraded-1",
      },
      readiness: {
        status: "degraded",
        service: "CodeMentor AI API",
        version: "0.1.0",
        database: "unavailable",
      },
      readinessHttpStatus: 503,
    };

    const fetcher = vi.fn().mockResolvedValue(degradedStatus);
    renderWithQueryClient(<SystemStatusCard fetchStatus={fetcher} />);

    await waitFor(() => {
      expect(screen.getByText("PostgreSQL: Unavailable")).toBeInTheDocument();
    });
  });

  it("renders an alert when the backend API is unreachable", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("Network error"));
    renderWithQueryClient(<SystemStatusCard fetchStatus={fetcher} />);

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Backend API unreachable",
      );
    });
    expect(screen.getByRole("alert")).toHaveTextContent("Network error");
  });
});
