import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import ExecutionJourney from "./ExecutionJourney";

const retryProps = {
  summary: {
    executionId: "exec-retry",
    state: "SUCCEEDED",
    technicalStatus: "SUCCESS",
    routeRef: "RETRY_THEN_SUCCESS@1",
    correlationRef: "corr-redacted",
    startedAt: "2026-09-03T12:00:00Z",
    updatedAt: "2026-09-03T12:00:03Z",
    completedAt: "2026-09-03T12:00:03Z",
    durationMs: 3000,
    completedSteps: 1,
    totalSteps: 1,
  },
  timeline: {
    available: true,
    data: [
      {
        eventId: "tr-1",
        eventType: "STATE_TRANSITION",
        state: "RUNNING",
        occurredAt: "2026-09-03T12:00:00Z",
        source: "PERSISTED",
      },
      {
        eventId: "att-1",
        eventType: "ATTEMPT",
        stepRef: "step-a",
        attemptNumber: 1,
        state: "FAILED",
        occurredAt: "2026-09-03T12:00:00Z",
        source: "PERSISTED",
      },
      {
        eventId: "att-2",
        eventType: "ATTEMPT",
        stepRef: "step-a",
        attemptNumber: 2,
        state: "SUCCEEDED",
        occurredAt: "2026-09-03T12:00:01Z",
        source: "PERSISTED",
      },
      {
        eventId: "tr-2",
        eventType: "STATE_TRANSITION",
        state: "SUCCEEDED",
        occurredAt: "2026-09-03T12:00:03Z",
        source: "PERSISTED",
      },
    ],
  },
  steps: {
    available: true,
    data: [
      {
        stepRef: "step-a",
        state: "SUCCEEDED",
        attemptCount: 2,
        attempts: [
          {
            attemptNumber: 1,
            state: "FAILED",
            disposition: "UNCERTAIN",
            safeErrorCode: "TRANSIENT",
            startedAt: "2026-09-03T12:00:00Z",
            completedAt: "2026-09-03T12:00:01Z",
          },
          {
            attemptNumber: 2,
            state: "SUCCEEDED",
            disposition: "CERTAIN",
            startedAt: "2026-09-03T12:00:01Z",
            completedAt: "2026-09-03T12:00:03Z",
          },
        ],
      },
    ],
  },
  waitInfo: { available: false },
  callback: { available: false },
  operationalEvents: [
    {
      eventId: "oe-1",
      eventType: "EXECUTION_STARTED",
      category: "EXECUTION",
      source: "canonical-engine",
      occurredAt: "2026-09-03T12:00:00Z",
    },
    {
      eventId: "oe-2",
      eventType: "EXECUTION_SUCCEEDED",
      category: "EXECUTION",
      source: "canonical-engine",
      outcome: "SUCCESS",
      occurredAt: "2026-09-03T12:00:03Z",
      metadata: { authorization: "Bearer secret-must-not-render" },
    },
    {
      eventId: "oe-other-attempt",
      eventType: "OUTBOUND_RESPONSE_RECEIVED",
      category: "TRANSPORT",
      source: "mock-adapter",
      metadata: { stepRef: "step-a", attemptNumber: "2" },
    },
  ],
};

describe("ExecutionJourney explainable steps", () => {
  it("selects terminal completion automatically and shows real totals", async () => {
    render(<ExecutionJourney {...retryProps} />);
    const completion = screen.getByRole("button", { name: /Execução concluída/ });
    await waitFor(() => expect(completion).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("A execução terminou em SUCCEEDED");
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("Tentativas");
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("Retries");
  });

  it("updates the panel when a failed interaction is selected", async () => {
    render(<ExecutionJourney {...retryProps} />);
    fireEvent.click(screen.getByRole("button", { name: /Interaction #1/ }));
    const panel = screen.getByTestId("journey-step-detail");
    expect(panel).toHaveTextContent("Interaction #1");
    expect(panel).toHaveTextContent("FAILED");
    expect(panel).toHaveTextContent("falha transitória");
    expect(panel).toHaveTextContent("TRANSIENT");
    expect(panel).toHaveTextContent("1 de 2");
    expect(panel).not.toHaveTextContent("HTTP Status");
  });

  it("explains retry origin and evidenced next attempt", () => {
    render(<ExecutionJourney {...retryProps} />);
    fireEvent.click(screen.getByRole("button", { name: /^↻?Retry/ }));
    const panel = screen.getByTestId("journey-step-detail");
    expect(panel).toHaveTextContent("Erro de origem");
    expect(panel).toHaveTextContent("TRANSIENT");
    expect(panel).toHaveTextContent("Próxima tentativa");
    expect(panel).toHaveTextContent("Executar a tentativa 2");
  });

  it("filters related events to the selected stage and keeps sensitive metadata redacted", () => {
    render(<ExecutionJourney {...retryProps} />);
    fireEvent.click(screen.getByRole("button", { name: /Interaction #1/ }));
    const panel = screen.getByTestId("journey-step-detail");
    fireEvent.click(screen.getByText(/Eventos relacionados/));
    expect(panel).toHaveTextContent("ATTEMPT");
    expect(panel).not.toHaveTextContent("OUTBOUND_RESPONSE_RECEIVED");
    expect(panel).not.toHaveTextContent("secret-must-not-render");
    expect(panel).toHaveTextContent("credenciais e payloads protegidos não são exibidos");
  });

  it("selects WAITING automatically and explains external continuity", async () => {
    render(
      <ExecutionJourney
        summary={{ executionId: "exec-wait", state: "WAITING_EXTERNAL", routeRef: "WAIT@1" }}
        timeline={{ available: true, data: [{ eventType: "WAIT_WAITING", state: "WAITING" }] }}
        steps={{ available: true, data: [] }}
        waitInfo={{
          available: true,
          data: { waitState: "WAITING", waitType: "SIGNAL", expiresAt: "2026-09-03T13:00:00Z" },
        }}
        callback={{ available: false }}
        operationalEvents={[{ eventType: "EXECUTION_WAITING", outcome: "WAITING" }]}
      />,
    );
    const wait = screen.getByRole("button", { name: /Wait \/ sinal externo/ });
    await waitFor(() => expect(wait).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent(
      "Aguardar callback ou signal correlacionado",
    );
  });

  it("selects the failed stage automatically for a terminal failure", async () => {
    render(
      <ExecutionJourney
        {...retryProps}
        summary={{
          ...retryProps.summary,
          executionId: "exec-failed",
          state: "FAILED",
          technicalStatus: "FAILURE",
        }}
        steps={{
          available: true,
          data: [
            {
              stepRef: "step-a",
              state: "FAILED",
              attemptCount: 1,
              attempts: [
                {
                  attemptNumber: 1,
                  state: "FAILED",
                  safeErrorCode: "TERMINAL",
                },
              ],
            },
          ],
        }}
      />,
    );
    const failed = screen.getByRole("button", { name: /Interaction #1/ });
    await waitFor(() => expect(failed).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent("TERMINAL");
  });

  it("preserves a manual selection while new execution evidence arrives", async () => {
    const { rerender } = render(
      <ExecutionJourney
        {...retryProps}
        summary={{ ...retryProps.summary, state: "RUNNING", completedAt: null }}
      />,
    );
    const request = screen.getByRole("button", { name: /Solicitação recebida/ });
    fireEvent.click(request);
    expect(request).toHaveAttribute("aria-pressed", "true");

    rerender(<ExecutionJourney {...retryProps} />);
    await waitFor(() => expect(request).toHaveAttribute("aria-pressed", "true"));
    expect(screen.getByTestId("journey-step-detail")).toHaveTextContent(
      "O Spider recebeu a solicitação",
    );
  });

  it("uses one accessible button per evidenced stage", () => {
    render(<ExecutionJourney {...retryProps} />);
    const stages = screen.getByLabelText("Etapas da jornada");
    expect(stages.querySelectorAll("button").length).toBe(8);
    expect(screen.getByRole("button", { name: /Interaction #2/ })).toHaveAttribute(
      "aria-controls",
      "journey-step-detail",
    );
  });
});
