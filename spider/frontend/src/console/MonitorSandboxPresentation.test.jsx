import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import MonitorShell from "./MonitorShell";

const EXECUTION_ID = "exec-sandbox-demo-20260928-r2";

const summary = {
  executionId: EXECUTION_ID,
  correlationRef: "corr-sandbox-demo-20260928-r2",
  routeRef: "demo-success_multi_step@1.0.0",
  operationRef: "demo-success_multi_step",
  state: "SUCCEEDED",
  technicalStatus: "SUCCESS",
  startedAt: "2026-09-28T17:36:20.715859565Z",
  completedAt: "2026-09-28T17:36:20.898556729Z",
  durationMs: 182,
};

const detail = {
  summary: { ...summary, completedSteps: 2, totalSteps: 2 },
  plan: {
    available: true,
    data: { planId: "plan-demo", routeRef: summary.routeRef, orderedSteps: ["step-1", "step-2"] },
  },
  steps: {
    available: true,
    data: [
      {
        stepRef: "step-1",
        order: 0,
        state: "SUCCEEDED",
        attemptCount: 1,
        attempts: [
          {
            attemptNumber: 1,
            attemptId: "att-14b848e2",
            state: "SUCCEEDED",
            disposition: "COMPLETED",
            startedAt: "2026-09-28T17:36:20.806Z",
            completedAt: "2026-09-28T17:36:20.816Z",
          },
        ],
      },
      {
        stepRef: "step-2",
        order: 1,
        state: "SUCCEEDED",
        attemptCount: 1,
        attempts: [
          {
            attemptNumber: 1,
            attemptId: "att-c95c8264",
            state: "SUCCEEDED",
            disposition: "COMPLETED",
            startedAt: "2026-09-28T17:36:20.894Z",
            completedAt: "2026-09-28T17:36:20.895Z",
          },
        ],
      },
    ],
  },
  timeline: { available: true, data: [] },
  waitInfo: { available: false },
  callback: { available: false },
};

function json(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => JSON.stringify(body),
  };
}

function installFetch({ contextStatus = 404, eventsStatus = 200, extraSummaries = [] } = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      const path = String(url);
      if (path.includes("/v1/console/monitor/events")) {
        return json({ available: true, items: [], availableScenarios: ["SUCCESS_MULTI_STEP"] });
      }
      if (path.includes(`/v1/console/executions/${EXECUTION_ID}/events`)) {
        if (eventsStatus !== 200) {
          return json(
            { title: "Unexpected orchestration error", status: eventsStatus, detail: "store unavailable" },
            eventsStatus,
          );
        }
        return json({ executionId: EXECUTION_ID, items: [] });
      }
      if (path.includes(`/v1/console/executions/${EXECUTION_ID}`)) {
        return json(detail);
      }
      if (path.includes("/v1/console/executions")) {
        return json({ items: [summary, ...extraSummaries] });
      }
      if (path.includes(`/v1/context/executions/${EXECUTION_ID}`)) {
        return json(
          { title: contextStatus === 404 ? "Resource not found" : "Unexpected orchestration error", status: contextStatus },
          contextStatus,
        );
      }
      return json({ items: [] });
    }),
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Monitor sandbox presentation", () => {
  beforeEach(() => installFetch());

  it("loads a SUCCEEDED execution without an orchestration error banner", async () => {
    render(<MonitorShell />);
    expect(await screen.findByRole("button", { name: /demo-success multi step/i })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: /Etapa 1 · tentativa 1/ })).toBeInTheDocument();
    expect(screen.queryByText(/Unexpected orchestration error/)).not.toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("keeps two legitimate multi-step attempts with distinct titles", async () => {
    render(<MonitorShell />);
    const first = await screen.findByRole("button", { name: /Etapa 1 · tentativa 1/ });
    const second = screen.getByRole("button", { name: /Etapa 2 · tentativa 1/ });
    expect(first).not.toBe(second);
    expect(screen.getAllByRole("button", { name: /Etapa 1 · tentativa 1/ })).toHaveLength(1);
    expect(screen.getAllByRole("button", { name: /Etapa 2 · tentativa 1/ })).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /Interaction #1/ })).not.toBeInTheDocument();
  });

  it("opens a distinct detail for each integration step", async () => {
    render(<MonitorShell />);
    fireEvent.click(await screen.findByRole("button", { name: /Etapa 1 · tentativa 1/ }));
    const panel = screen.getByTestId("journey-step-detail");
    expect(panel).toHaveTextContent("Etapa 1 · tentativa 1");
    expect(panel).toHaveTextContent("step-1");
    expect(panel).toHaveTextContent("att-14b848e2");
    fireEvent.click(screen.getByRole("button", { name: /Etapa 2 · tentativa 1/ }));
    expect(panel).toHaveTextContent("Etapa 2 · tentativa 1");
    expect(panel).toHaveTextContent("step-2");
    expect(panel).toHaveTextContent("att-c95c8264");
    expect(panel).not.toHaveTextContent("att-14b848e2");
  });

  it("preserves the selected transaction after a poll refresh", async () => {
    render(<MonitorShell />);
    fireEvent.click(await screen.findByRole("button", { name: /Etapa 2 · tentativa 1/ }));
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("Etapa 2 · tentativa 1");
    fireEvent.click(screen.getByRole("button", { name: "Atualizar" }));
    await waitFor(() =>
      expect(fetch.mock.calls.filter(([url]) => String(url).includes("/v1/console/executions?")).length).toBeGreaterThan(1),
    );
    expect(screen.getByRole("button", { name: /demo-success multi step/i })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("Etapa 2 · tentativa 1");
    expect(screen.queryByText(/Unexpected orchestration error/)).not.toBeInTheDocument();
  });

  it("keeps related-events failures inside the related events section", async () => {
    installFetch({ eventsStatus: 500 });
    render(<MonitorShell />);
    fireEvent.click(await screen.findByRole("button", { name: /Etapa 1 · tentativa 1/ }));
    expect(screen.queryByText(/Unexpected orchestration error/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Não foi possível consultar o plano persistido/)).not.toBeInTheDocument();
    const related = await screen.findByTestId("related-events-error");
    expect(related).toHaveTextContent("Consulta de eventos relacionados falhou");
    expect(related).toHaveTextContent("store unavailable");
    expect(related.closest(".journey-related-events")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Transação selecionada" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /demo-success multi step/i })).toBeInTheDocument();
  });
});
