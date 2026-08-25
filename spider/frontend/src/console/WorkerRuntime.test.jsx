import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import WorkerRuntime, {
  canDrainWorker,
  formatAgeMs,
  formatInterval,
  heartbeatAgeMs,
} from "./WorkerRuntime.jsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

const CALCULATED_AT = "2026-08-25T12:00:00Z";

const SNAPSHOT = {
  schemaVersion: 1,
  calculatedAt: CALCULATED_AT,
  boundary: "SIMULATED_INFRASTRUCTURE",
  integrationBoundary: "MOCK_ONLY",
  runtimeStatus: "HEALTHY",
  workers: [
    {
      workerId: "wrk-inst-1:signal_application",
      runtimeInstanceId: "wrk-inst-1",
      workerType: "SIGNAL_APPLICATION",
      status: "RUNNING",
      startedAt: "2026-08-25T11:00:00Z",
      lastHeartbeatAt: "2026-08-25T11:59:55Z",
      drainRequestedAt: null,
      stoppedAt: null,
      currentClaims: 2,
      processedCount: 41,
      failureCount: 3,
      version: 12,
    },
    {
      workerId: "wrk-inst-1:wait_expiry",
      runtimeInstanceId: "wrk-inst-1",
      workerType: "WAIT_EXPIRY",
      status: "STALE",
      startedAt: "2026-08-25T11:00:00Z",
      lastHeartbeatAt: "2026-08-25T11:52:00Z",
      drainRequestedAt: null,
      stoppedAt: null,
      currentClaims: 0,
      processedCount: 7,
      failureCount: 0,
      version: 9,
    },
  ],
  schedules: [
    {
      scheduleCode: "schedule:signal-application",
      version: 4,
      scheduleVersion: "1.0",
      workerType: "SIGNAL_APPLICATION",
      enabled: true,
      interval: "PT10S",
      nextEligibleAt: "2026-08-25T12:00:10Z",
      lastStartedAt: "2026-08-25T11:59:50Z",
      lastCompletedAt: "2026-08-25T11:59:51Z",
      lastOutcome: "SUCCESS",
      ownerWorkerId: "wrk-inst-1:signal_application",
      leaseUntil: "2026-08-25T12:00:30Z",
      fencingToken: 37,
    },
  ],
  backlogs: [
    {
      schemaVersion: 1,
      workerType: "SIGNAL_APPLICATION",
      status: "ACCUMULATING",
      eligibleCount: 18,
      oldestEligibleAgeMs: 125000,
      approximate: false,
      explanation: "Backlog acima do limiar configurado.",
    },
    {
      schemaVersion: 1,
      workerType: "WAIT_EXPIRY",
      status: "EMPTY",
      eligibleCount: 0,
      oldestEligibleAgeMs: null,
      approximate: false,
      explanation: "",
    },
  ],
  staleWorkers: 1,
  expiredLeases: 0,
  oldestPendingAgeMs: 125000,
  dataQuality: {
    schemaVersion: 1,
    complete: true,
    resultLimitReached: false,
    availableSources: ["workerInstanceStore", "durableScheduleStore"],
    missingSources: [],
    warnings: [],
  },
};

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) };
}

function stubSnapshot(snapshot = SNAPSHOT) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url, init) => {
      if (String(url).endsWith("/v1/console/runtime") && (!init || init.method !== "POST")) {
        return jsonResponse(snapshot);
      }
      return jsonResponse({ title: "Not Found", status: 404 }, 404);
    }),
  );
}

describe("WorkerRuntime helpers", () => {
  it("formats ages from milliseconds", () => {
    expect(formatAgeMs(null)).toBe("—");
    expect(formatAgeMs(450)).toBe("450 ms");
    expect(formatAgeMs(5000)).toBe("5 s");
    expect(formatAgeMs(125000)).toBe("2 min 5 s");
    expect(formatAgeMs(7200000)).toBe("2 h");
  });

  it("formats the schedule interval from ISO-8601 or seconds", () => {
    expect(formatInterval("PT10S")).toBe("10 s");
    expect(formatInterval("PT2M")).toBe("2 min");
    expect(formatInterval(30)).toBe("30 s");
    expect(formatInterval(null)).toBe("—");
  });

  it("measures heartbeat age against the snapshot reference", () => {
    expect(heartbeatAgeMs(SNAPSHOT.workers[0], CALCULATED_AT)).toBe(5000);
    expect(heartbeatAgeMs({ lastHeartbeatAt: null }, CALCULATED_AT)).toBeNull();
  });

  it("allows drain only for running or idle workers not already draining", () => {
    expect(canDrainWorker({ status: "RUNNING" })).toBe(true);
    expect(canDrainWorker({ status: "IDLE" })).toBe(true);
    expect(canDrainWorker({ status: "DRAINING" })).toBe(false);
    expect(canDrainWorker({ status: "STOPPED" })).toBe(false);
    expect(canDrainWorker({ status: "STALE" })).toBe(false);
    expect(canDrainWorker({ status: "RUNNING", drainRequestedAt: CALCULATED_AT })).toBe(false);
  });
});

describe("WorkerRuntime", () => {
  it("renders the permanent simulated infrastructure banner", async () => {
    stubSnapshot();
    render(<WorkerRuntime />);
    const banner = await screen.findByTestId("worker-runtime-boundary-banner");
    expect(banner).toHaveTextContent("INFRAESTRUTURA SIMULADA");
    expect(banner).toHaveTextContent("INTEGRAÇÕES MOCK_ONLY");
    expect(banner).toHaveTextContent("NÃO PRODUTIVO");
  });

  it("shows workers, schedules and backlogs from the snapshot", async () => {
    stubSnapshot();
    render(<WorkerRuntime />);

    const running = await screen.findByTestId(
      "worker-runtime-worker-wrk-inst-1:signal_application",
    );
    expect(running).toHaveTextContent("Aplicação de sinal");
    expect(running).toHaveTextContent("Processando (RUNNING)");
    expect(running).toHaveTextContent("5 s");
    expect(running).toHaveTextContent("Não solicitada");
    expect(running).toHaveTextContent("41");
    expect(running).toHaveTextContent("3");

    const stale = screen.getByTestId("worker-runtime-worker-wrk-inst-1:wait_expiry");
    expect(stale).toHaveTextContent("Sem heartbeat (STALE)");

    expect(screen.getByTestId("worker-runtime-status")).toHaveTextContent("Saudável (HEALTHY)");
    expect(screen.getByTestId("worker-runtime-stale-workers")).toHaveTextContent("1");
    expect(screen.getByTestId("worker-runtime-expired-leases")).toHaveTextContent("0");
    expect(screen.getByTestId("worker-runtime-calculated-at")).not.toBeEmptyDOMElement();

    const schedule = screen.getByTestId("worker-runtime-schedule-schedule:signal-application");
    expect(schedule).toHaveTextContent("schedule:signal-application");
    expect(schedule).toHaveTextContent("37");
    expect(schedule).toHaveTextContent("Sucesso (SUCCESS)");
    expect(schedule).toHaveTextContent("wrk-inst-1:signal_application");

    const backlog = screen.getByTestId("worker-runtime-backlog-SIGNAL_APPLICATION");
    expect(backlog).toHaveTextContent("Acumulando (ACCUMULATING)");
    expect(backlog).toHaveTextContent("18");
    expect(backlog).toHaveTextContent("2 min 5 s");
  });

  it("shows the disabled state when the capability responds 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Not Found", status: 404 }, 404)),
    );
    render(<WorkerRuntime />);
    await waitFor(() => expect(screen.getByText(/Capability desabilitada/i)).toBeInTheDocument());
    expect(screen.queryByTestId("worker-runtime-workers")).not.toBeInTheDocument();
    expect(screen.getByTestId("worker-runtime-boundary-banner")).toBeInTheDocument();
  });

  it("shows the disabled state when the runtime reports DISABLED", async () => {
    stubSnapshot({
      ...SNAPSHOT,
      runtimeStatus: "DISABLED",
      workers: [],
      schedules: [],
      backlogs: [],
    });
    render(<WorkerRuntime />);
    await waitFor(() => expect(screen.getByText(/Capability desabilitada/i)).toBeInTheDocument());
    expect(screen.queryByTestId("worker-runtime-summary")).not.toBeInTheDocument();
  });

  it("shows the unauthorized state when the credential is rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Forbidden", status: 403 }, 403)),
    );
    render(<WorkerRuntime />);
    await waitFor(() =>
      expect(screen.getByText(/sem permissão para o runtime de workers/i)).toBeInTheDocument(),
    );
  });

  it("shows the empty state without treating it as healthy", async () => {
    stubSnapshot({ ...SNAPSHOT, runtimeStatus: "UNKNOWN", workers: [], staleWorkers: 0 });
    render(<WorkerRuntime />);
    await waitFor(() =>
      expect(screen.getByText(/sem nenhuma instância registrada/i)).toBeInTheDocument(),
    );
    expect(screen.getByTestId("worker-runtime-status")).toHaveTextContent("Indeterminado");
  });

  it("reports partial data quality instead of assuming a healthy runtime", async () => {
    stubSnapshot({
      ...SNAPSHOT,
      dataQuality: {
        ...SNAPSHOT.dataQuality,
        complete: false,
        missingSources: ["WAIT_EXPIRY"],
        warnings: ["Backlog counts capped at maxScan=500"],
      },
    });
    render(<WorkerRuntime />);
    const partial = await screen.findByTestId("worker-runtime-partial");
    expect(partial).toHaveTextContent("WAIT_EXPIRY");
    expect(partial).toHaveTextContent("maxScan=500");
  });

  it("offers drain only for eligible workers and requires explicit confirmation", async () => {
    stubSnapshot();
    render(<WorkerRuntime />);
    const drain = await screen.findByTestId(
      "worker-runtime-drain-wrk-inst-1:signal_application",
    );
    expect(
      screen.queryByTestId("worker-runtime-drain-wrk-inst-1:wait_expiry"),
    ).not.toBeInTheDocument();

    fireEvent.click(drain);
    expect(screen.getByTestId("worker-runtime-drain-confirmation")).toHaveTextContent(
      /simulada no ambiente local-demo/i,
    );
    expect(fetch.mock.calls.some((call) => String(call[0]).includes("/drain"))).toBe(false);
  });

  it("posts the drain request after confirmation", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) => {
        if (String(url).includes("/drain") && init?.method === "POST") {
          return jsonResponse({ ...SNAPSHOT.workers[0], status: "DRAINING" }, 202);
        }
        return jsonResponse(SNAPSHOT);
      }),
    );
    render(<WorkerRuntime />);
    fireEvent.click(
      await screen.findByTestId("worker-runtime-drain-wrk-inst-1:signal_application"),
    );
    fireEvent.click(
      screen.getByTestId("worker-runtime-drain-confirm-wrk-inst-1:signal_application"),
    );
    await waitFor(() =>
      expect(screen.getByTestId("worker-runtime-drain-message")).toHaveTextContent(
        /Drenagem simulada solicitada/i,
      ),
    );
    const drainCall = fetch.mock.calls.find((call) => String(call[0]).includes("/drain"));
    expect(drainCall[0]).toBe(
      "/v1/console/runtime/workers/wrk-inst-1%3Asignal_application/drain",
    );
    expect(drainCall[1].method).toBe("POST");
  });

  it("surfaces a safe message when the drain endpoint is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url, init) => {
        if (String(url).includes("/drain") && init?.method === "POST") {
          return jsonResponse({ title: "Not Found", status: 404 }, 404);
        }
        return jsonResponse(SNAPSHOT);
      }),
    );
    render(<WorkerRuntime />);
    fireEvent.click(
      await screen.findByTestId("worker-runtime-drain-wrk-inst-1:signal_application"),
    );
    fireEvent.click(
      screen.getByTestId("worker-runtime-drain-confirm-wrk-inst-1:signal_application"),
    );
    await waitFor(() =>
      expect(screen.getByTestId("worker-runtime-drain-message")).toHaveTextContent(
        /Drenagem indisponível ou não autorizada/i,
      ),
    );
  });

  it("does not claim production readiness, SLAs or availability targets", async () => {
    stubSnapshot();
    const { container } = render(<WorkerRuntime />);
    await screen.findByTestId("worker-runtime-workers");
    const text = container.textContent;
    expect(text).toContain("NÃO PRODUTIVO");
    expect(text).not.toMatch(/em produç[ãa]o/i);
    expect(text).not.toMatch(/pronto para produç[ãa]o/i);
    expect(text).not.toMatch(/production[- ]ready/i);
    expect(text).not.toMatch(/\bSLA\b/);
    expect(text).not.toMatch(/\d+([.,]\d+)?\s*%/);
    expect(text).not.toMatch(/99[.,]9/);
  });
});
