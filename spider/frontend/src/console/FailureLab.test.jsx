import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import FailureLab, { formatMaximumDuration, isActiveRunStatus } from "./FailureLab.jsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const CATALOG = {
  schemaVersion: 1,
  boundary: "MOCK_ONLY",
  scenarios: [
    {
      schemaVersion: 1,
      code: "RETRY_THEN_SUCCESS",
      version: "1.0",
      title: "Falha transitória seguida de sucesso",
      functionalDescription:
        "Demonstra que uma indisponibilidade momentânea do parceiro simulado é absorvida pela retentativa.",
      category: "RETRY",
      targetBoundary: "MOCK_ONLY",
      preconditions: ["Adapter mock habilitado"],
      allowedParameterKeys: ["note"],
      expectedObservations: [
        {
          code: "EXECUTION_SUCCEEDED",
          description: "A execução termina em sucesso técnico após a retentativa.",
          sourceType: "EXECUTION_CONTROL",
          predicateType: "EXECUTION_REACHED_STATE",
          expectedValue: "SUCCEEDED",
          required: true,
        },
      ],
      maximumDuration: "PT2M",
      maximumExecutions: 1,
      runbookRef: "runbook:failure-lab:retry@1.0",
      mockScenario: "RETRY_THEN_SUCCESS",
      operationCode: "RETRY_THEN_SUCCESS",
    },
    {
      schemaVersion: 1,
      code: "INSUFFICIENT_SAMPLE",
      version: "1.0",
      title: "Amostra insuficiente para conclusão operacional",
      functionalDescription:
        "Demonstra que, sem volume mínimo de observações, os indicadores declaram amostra insuficiente.",
      category: "OPERATIONAL_HEALTH",
      targetBoundary: "MOCK_ONLY",
      preconditions: [],
      allowedParameterKeys: [],
      expectedObservations: [
        {
          code: "SLI_INSUFFICIENT_DATA",
          description: "Ao menos um indicador declara amostra insuficiente.",
          sourceType: "OPERATIONAL_HEALTH",
          predicateType: "SLI_STATUS_EQUALS",
          expectedValue: "INSUFFICIENT_DATA",
          required: false,
        },
      ],
      maximumDuration: "PT1M",
      maximumExecutions: 0,
      runbookRef: "runbook:failure-lab:health@1.0",
      mockScenario: null,
      operationCode: null,
    },
  ],
  runbooks: [
    {
      schemaVersion: 1,
      code: "runbook:failure-lab:retry",
      version: "1.0",
      title: "Runbook Mock — retentativa",
      purpose: "Orientar a leitura de uma falha transitória absorvida pela retentativa.",
      applicableScenarioRefs: ["RETRY_THEN_SUCCESS@1.0"],
      symptoms: ["Primeira tentativa falha e a seguinte conclui"],
      checks: ["Conferir a contagem de tentativas do primeiro passo"],
      expectedEvidence: ["Execução em sucesso técnico"],
      safeActions: ["Nenhuma ação corretiva é necessária"],
      stopConditions: ["Falha permanece após o limite de tentativas"],
      escalationGuidance: "Registrar o caso na trilha de demonstração Mock.",
      limitations: "Runbook provisório MOCK_ONLY — não substitui procedimento de produção.",
    },
  ],
};

const RUN = {
  schemaVersion: 1,
  labRunId: "labrun-1",
  scenarioCode: "RETRY_THEN_SUCCESS",
  scenarioVersion: "1.0",
  requestedAt: "2026-08-25T12:00:00Z",
  requestedBy: "principal:local-demo",
  startedAt: "2026-08-25T12:00:00Z",
  completedAt: "2026-08-25T12:00:04Z",
  status: "VERIFIED",
  boundary: "MOCK_ONLY",
  parameters: {},
  executionRefs: ["ex-1"],
  verificationResults: [
    {
      observationCode: "EXECUTION_SUCCEEDED",
      status: "PASSED",
      observedAt: "2026-08-25T12:00:03Z",
      expected: "SUCCEEDED",
      observed: "SUCCEEDED",
      safeReferences: {},
      explanation: "Execução alcançou o estado esperado.",
    },
    {
      observationCode: "TELEMETRY_EXECUTION_SUCCEEDED",
      status: "NOT_OBSERVED",
      observedAt: null,
      expected: "EXECUTION_SUCCEEDED",
      observed: "",
      safeReferences: {},
      explanation: "Telemetria desabilitada nesta execução.",
    },
  ],
  evidenceSummary: "1 atendida, 1 não observada",
  failureMessage: null,
};

const EVIDENCE = {
  schemaVersion: 1,
  evidenceId: "labev-1",
  labRunId: "labrun-1",
  scenarioRef: "RETRY_THEN_SUCCESS@1.0",
  boundary: "MOCK_ONLY",
  generatedAt: "2026-08-25T12:00:05Z",
  executionRefs: ["ex-1"],
  verificationResults: RUN.verificationResults,
  redactionStatus: "APPLIED",
  completenessStatus: "COMPLETE",
  digest: "a1b2c3d4e5f6",
};

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) };
}

function stubCatalogOnly() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      if (String(url).includes("/v1/console/failure-lab/scenarios")) {
        return jsonResponse(CATALOG);
      }
      return jsonResponse({ title: "Not Found", status: 404 }, 404);
    }),
  );
}

describe("FailureLab helpers", () => {
  it("formats maximumDuration from ISO-8601 and from seconds", () => {
    expect(formatMaximumDuration("PT2M")).toBe("2 min");
    expect(formatMaximumDuration(120)).toBe("2 min");
    expect(formatMaximumDuration(45)).toBe("45 s");
    expect(formatMaximumDuration(null)).toBe("—");
  });

  it("treats only pre-terminal lifecycle states as active", () => {
    expect(isActiveRunStatus("RUNNING")).toBe(true);
    expect(isActiveRunStatus("OBSERVING")).toBe(true);
    expect(isActiveRunStatus("VERIFIED")).toBe(false);
    expect(isActiveRunStatus("INCONCLUSIVE")).toBe(false);
  });
});

describe("FailureLab", () => {
  it("renders the permanent mock boundary banner", async () => {
    stubCatalogOnly();
    render(<FailureLab />);
    const banner = await screen.findByTestId("failure-lab-boundary-banner");
    expect(banner).toHaveTextContent("AMBIENTE DE DEMONSTRAÇÃO");
    expect(banner).toHaveTextContent("MOCK_ONLY");
    expect(banner).toHaveTextContent("FALHAS SIMULADAS");
    expect(banner).toHaveTextContent("SEM CONEXÃO COM LEGADOS REAIS");
  });

  it("shows scenarios returned by the catalog API", async () => {
    stubCatalogOnly();
    render(<FailureLab />);
    await waitFor(() =>
      expect(screen.getByTestId("failure-lab-scenario-RETRY_THEN_SUCCESS")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("failure-lab-scenario-INSUFFICIENT_SAMPLE")).toBeInTheDocument();
    expect(screen.getByText("Falha transitória seguida de sucesso")).toBeInTheDocument();
    expect(screen.getByText("Retentativa")).toBeInTheDocument();
    expect(screen.getByText("2 min")).toBeInTheDocument();
    expect(screen.getByText("runbook:failure-lab:retry@1.0")).toBeInTheDocument();
  });

  it("shows the disabled state when the capability responds 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Not Found", status: 404 }, 404)),
    );
    render(<FailureLab />);
    await waitFor(() =>
      expect(screen.getByText(/Capability desabilitada/i)).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("failure-lab-scenario-RETRY_THEN_SUCCESS")).not.toBeInTheDocument();
    expect(screen.getByTestId("failure-lab-boundary-banner")).toBeInTheDocument();
  });

  it("shows the unauthorized state when the credential is rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Forbidden", status: 403 }, 403)),
    );
    render(<FailureLab />);
    await waitFor(() =>
      expect(screen.getByText(/sem permissão para o Failure Lab/i)).toBeInTheDocument(),
    );
  });

  it("shows the empty state when the catalog has no scenarios", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ ...CATALOG, scenarios: [], runbooks: [] })),
    );
    render(<FailureLab />);
    await waitFor(() =>
      expect(screen.getByText(/Catálogo publicado sem cenários/i)).toBeInTheDocument(),
    );
  });

  it("requires explicit confirmation before starting a run", async () => {
    stubCatalogOnly();
    render(<FailureLab />);
    fireEvent.click(await screen.findByTestId("failure-lab-select-RETRY_THEN_SUCCESS"));
    expect(screen.getByTestId("failure-lab-confirmation")).toHaveTextContent(
      "Este cenário criará execuções e eventos técnicos somente no ambiente Mock. Nenhum legado real será acessado.",
    );
    expect(screen.getByRole("button", { name: "Executar cenário" })).toBeDisabled();
    expect(
      fetch.mock.calls.some((call) => String(call[0]).includes("/failure-lab/runs")),
    ).toBe(false);
  });

  it("runs a scenario, shows the journey, verifications and evidence", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) => {
        const target = String(url);
        if (target.includes("/failure-lab/scenarios")) return jsonResponse(CATALOG);
        if (target.includes("/failure-lab/runs") && init?.method === "POST") {
          return jsonResponse(RUN, 202);
        }
        if (target.includes("/evidence")) return jsonResponse(EVIDENCE);
        return jsonResponse({ title: "Not Found", status: 404 }, 404);
      }),
    );
    const onOpenExecution = vi.fn();
    render(<FailureLab onOpenExecution={onOpenExecution} />);

    fireEvent.click(await screen.findByTestId("failure-lab-select-RETRY_THEN_SUCCESS"));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Executar cenário" }));

    await waitFor(() =>
      expect(screen.getByTestId("failure-lab-run-status")).toHaveTextContent("Verificado"),
    );
    expect(screen.getByTestId("failure-lab-journey-VERIFICAR")).toHaveTextContent("Concluído");
    expect(screen.getByTestId("failure-lab-verification-EXECUTION_SUCCEEDED")).toHaveTextContent(
      "Atendido",
    );
    expect(
      screen.getByTestId("failure-lab-verification-TELEMETRY_EXECUTION_SUCCEEDED"),
    ).toHaveTextContent("Não observado");

    await waitFor(() => expect(screen.getByTestId("failure-lab-evidence")).toBeInTheDocument());
    expect(screen.getByText("a1b2c3d4e5f6")).toBeInTheDocument();
    expect(screen.getByText("Completa")).toBeInTheDocument();
    expect(screen.getByText("Aplicada")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Abrir execução ex-1/ }));
    expect(onOpenExecution).toHaveBeenCalledWith("ex-1");
  });

  it("renders the runbook from the catalog payload for the selected scenario", async () => {
    stubCatalogOnly();
    render(<FailureLab />);
    fireEvent.click(await screen.findByTestId("failure-lab-select-RETRY_THEN_SUCCESS"));
    const runbook = screen.getByTestId("failure-lab-runbook");
    expect(runbook).toHaveTextContent("Runbook Mock — retentativa");
    expect(runbook).toHaveTextContent("Orientar a leitura de uma falha transitória");
    expect(runbook).toHaveTextContent("Condições de parada");
  });

  it("does not hardcode SLI percentages or availability targets", async () => {
    stubCatalogOnly();
    const { container } = render(<FailureLab />);
    await screen.findByTestId("failure-lab-scenario-RETRY_THEN_SUCCESS");
    expect(container.textContent).not.toMatch(/\d+([.,]\d+)?\s*%/);
    expect(container.textContent).not.toMatch(/99[.,]9/);
  });

  it("surfaces a safe message when the run endpoint is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) => {
        const target = String(url);
        if (target.includes("/failure-lab/scenarios")) return jsonResponse(CATALOG);
        if (target.includes("/failure-lab/runs") && init?.method === "POST") {
          return jsonResponse({ title: "Not Found", status: 404 }, 404);
        }
        return jsonResponse({ title: "Not Found", status: 404 }, 404);
      }),
    );
    render(<FailureLab />);
    fireEvent.click(await screen.findByTestId("failure-lab-select-RETRY_THEN_SUCCESS"));
    fireEvent.click(screen.getByRole("checkbox"));
    fireEvent.click(screen.getByRole("button", { name: "Executar cenário" }));
    await waitFor(() =>
      expect(screen.getByText(/Failure Lab indisponível ou não autorizado/i)).toBeInTheDocument(),
    );
    expect(screen.queryByTestId("failure-lab-run-status")).not.toBeInTheDocument();
  });
});
