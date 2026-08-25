import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import CapacityResilience, {
  BOUNDARY_BANNER_TEXT,
  STALE_AFTER_MS,
  capacityModeLabel,
  capacityViewState,
  circuitTransitionNote,
  formatLimit,
  freshnessText,
  summarizePressure,
} from "./CapacityResilience.jsx";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function snapshotFixture(overrides = {}) {
  const now = new Date().toISOString();
  return {
    schemaVersion: 1,
    calculatedAt: now,
    boundary: "SIMULATED_INFRASTRUCTURE",
    integrationBoundary: "MOCK_ONLY",
    mode: "ENFORCED",
    policies: [
      {
        code: "capacity:global",
        version: "1.0",
        scopeType: "GLOBAL",
        scopeRef: "GLOBAL",
        state: "ACTIVE",
        limits: {
          maxConcurrency: 8,
          softBacklogLimit: 20,
          hardBacklogLimit: 50,
          quotaPerWindow: 120,
          window: "PT1M",
          acquireTimeout: "PT0S",
        },
        circuitFailureThreshold: 5,
        circuitWindow: "PT1M",
        circuitOpenDuration: "PT30S",
        circuitProbeLimit: 1,
        precedence: 1,
        enforced: true,
      },
    ],
    pressure: [
      {
        schemaVersion: 1,
        scopeKey: "GLOBAL:GLOBAL",
        scopeType: "GLOBAL",
        scopeRef: "GLOBAL",
        policyRef: "capacity:global@1.0",
        level: "ELEVATED",
        occupied: 6,
        capacity: 8,
        utilizationPercent: 75,
        backlogCount: 12,
        softBacklogLimit: 20,
        hardBacklogLimit: 50,
        quotaUsed: 44,
        quotaLimit: 120,
        circuitPhase: "CLOSED",
        observedAt: now,
        explanation: "Escopo com ocupação acima do confortável.",
      },
      {
        schemaVersion: 1,
        scopeKey: "WORKER_TYPE:CALLBACK_DELIVERY",
        scopeType: "WORKER_TYPE",
        scopeRef: "CALLBACK_DELIVERY",
        policyRef: "capacity:worker:callback@1.0",
        level: "CRITICAL",
        occupied: 4,
        capacity: 4,
        utilizationPercent: 100,
        backlogCount: 61,
        softBacklogLimit: 10,
        hardBacklogLimit: 40,
        quotaUsed: 0,
        quotaLimit: 0,
        circuitPhase: "OPEN",
        observedAt: now,
        explanation: "Escopo em pressão crítica: proteção de capacidade acionada.",
      },
    ],
    bulkheads: [
      {
        scopeKey: "WORKER_TYPE:CALLBACK_DELIVERY",
        capacity: 4,
        occupied: 4,
        waiting: 3,
        updatedAt: now,
      },
    ],
    circuits: [
      {
        scopeKey: "WORKER_TYPE:CALLBACK_DELIVERY",
        phase: "OPEN",
        failureCount: 5,
        successCount: 0,
        openedAt: now,
        probeAfter: now,
        probeInFlight: 0,
        updatedAt: now,
      },
    ],
    recentDecisions: [
      {
        decisionId: "dec-1",
        requestedAt: now,
        decidedAt: now,
        result: "SHED",
        reasonCode: "BACKLOG_HARD_LIMIT",
        policyRef: "capacity:worker:callback@1.0",
        policyVersion: "1.0",
        scopeType: "WORKER_TYPE",
        scopeRef: "CALLBACK_DELIVERY",
        shedReason: "BACKLOG_HARD_LIMIT",
        monitorOnly: false,
        correlationRef: null,
      },
    ],
    dataQuality: {
      schemaVersion: 1,
      complete: true,
      resultLimitReached: false,
      availableSources: ["capacityPolicyCatalog", "capacityRuntimeState"],
      missingSources: [],
      warnings: [],
    },
    ...overrides,
  };
}

function jsonResponse(body, status = 200) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) };
}

function stubSnapshot(snapshot = snapshotFixture(), decisions = null) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url) => {
      const target = String(url);
      if (target.includes("/v1/console/capacity/decisions")) {
        return decisions
          ? jsonResponse({ decisions })
          : jsonResponse({ title: "Not Found", status: 404 }, 404);
      }
      if (target.endsWith("/v1/console/capacity")) {
        return jsonResponse(snapshot);
      }
      return jsonResponse({ title: "Not Found", status: 404 }, 404);
    }),
  );
}

describe("CapacityResilience helpers", () => {
  it("labels the governance modes in Portuguese", () => {
    expect(capacityModeLabel("MONITOR_ONLY")).toBe("Somente observação");
    expect(capacityModeLabel("ENFORCED")).toBe("Aplicando limites");
    expect(capacityModeLabel("DISABLED")).toBe("Desabilitado");
    expect(capacityModeLabel(null)).toBe("—");
  });

  it("derives the view state without assuming a fresh reading", () => {
    const now = Date.parse("2026-08-25T12:00:00Z");
    const fresh = { mode: "ENFORCED", pressure: [{ level: "NORMAL" }], calculatedAt: "2026-08-25T11:59:50Z" };
    expect(capacityViewState(fresh, now)).toBe("ready");
    expect(capacityViewState({ ...fresh, calculatedAt: "2026-08-25T11:00:00Z" }, now)).toBe("stale");
    expect(capacityViewState({ ...fresh, calculatedAt: null }, now)).toBe("stale");
    expect(capacityViewState({ ...fresh, mode: "DISABLED" }, now)).toBe("disabled");
    expect(capacityViewState({ mode: "MONITOR_ONLY", calculatedAt: fresh.calculatedAt }, now)).toBe(
      "empty",
    );
    expect(capacityViewState(null, now)).toBe("empty");
  });

  it("reports an absent limit as a disabled protection, never as slack", () => {
    expect(formatLimit(-1)).toBe("sem limite");
    expect(formatLimit(0, { zeroMeansNoLimit: true })).toBe("sem limite");
    expect(formatLimit(0)).toBe("0");
    expect(formatLimit(40)).toBe("40");
  });

  it("marks an old observation as aged", () => {
    const now = Date.parse("2026-08-25T12:00:00Z");
    expect(freshnessText("2026-08-25T11:59:55Z", now)).toBe("5 s atrás");
    expect(freshnessText(new Date(now - STALE_AFTER_MS - 60_000).toISOString(), now)).toContain(
      "envelhecida",
    );
    expect(freshnessText(null, now)).toBe("Sem marca de tempo");
  });

  it("summarizes the worst observed pressure", () => {
    const summary = summarizePressure([{ level: "NORMAL" }, { level: "CRITICAL" }, { level: "HIGH" }]);
    expect(summary.worst).toBe("CRITICAL");
    expect(summary.total).toBe(3);
    expect(summary.counts.HIGH).toBe(1);
    expect(summarizePressure([]).worst).toBeNull();
  });

  it("describes the circuit transition only from published data", () => {
    expect(circuitTransitionNote({ phase: "CLOSED", updatedAt: "2026-08-25T12:00:00Z" })).toBeNull();
    expect(
      circuitTransitionNote({ phase: "OPEN", openedAt: "2026-08-25T12:00:00Z", failureCount: 5 }),
    ).toContain("5 falha(s)");
    expect(
      circuitTransitionNote({ phase: "CLOSED", lastTransitionReason: "PROBE_SUCCEEDED" }),
    ).toBe("PROBE_SUCCEEDED");
  });
});

describe("CapacityResilience", () => {
  it("renders the permanent boundary banner", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    const banner = await screen.findByTestId("capacity-boundary-banner");
    expect(banner).toHaveTextContent(BOUNDARY_BANNER_TEXT);
    expect(banner).toHaveTextContent("INFRAESTRUTURA SIMULADA");
    expect(banner).toHaveTextContent("SEM CAPACIDADE PRODUTIVA AFERIDA");
  });

  it("keeps the boundary banner even when the capability is unavailable", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Not Found", status: 404 }, 404)),
    );
    render(<CapacityResilience />);
    await screen.findByTestId("capacity-disabled");
    expect(screen.getByTestId("capacity-boundary-banner")).toHaveTextContent(
      "SEM CAPACIDADE PRODUTIVA AFERIDA",
    );
  });

  it("shows the mode, the pressure summary and the calculation timestamp", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    expect(await screen.findByTestId("capacity-mode")).toHaveTextContent(
      "Aplicando limites (ENFORCED)",
    );
    expect(screen.getByTestId("capacity-worst-pressure")).toHaveTextContent("Crítica (CRITICAL)");
    expect(screen.getByTestId("capacity-scope-count")).toHaveTextContent("2");
    expect(screen.getByTestId("capacity-calculated-at")).not.toBeEmptyDOMElement();
    expect(screen.getByTestId("capacity-mode-note")).toHaveTextContent(/Limites aplicados/i);
  });

  it("renders the monitor-only mode without claiming enforcement", async () => {
    stubSnapshot(snapshotFixture({ mode: "MONITOR_ONLY" }));
    render(<CapacityResilience />);
    expect(await screen.findByTestId("capacity-mode")).toHaveTextContent(
      "Somente observação (MONITOR_ONLY)",
    );
    expect(screen.getByTestId("capacity-mode-note")).toHaveTextContent(/sem recusar trabalho/i);
  });

  it("shows pressure by scope with a textual status, not colour alone", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    const row = await screen.findByTestId("capacity-pressure-WORKER_TYPE:CALLBACK_DELIVERY");
    expect(row).toHaveTextContent("Crítica (CRITICAL)");
    expect(row).toHaveTextContent("4 / 4");
    expect(row).toHaveTextContent("61");
    expect(row).toHaveTextContent("rígido 40");
    expect(row).toHaveTextContent("Aberto (OPEN)");
    expect(row).toHaveTextContent("sem limite");

    const global = screen.getByTestId("capacity-pressure-GLOBAL:GLOBAL");
    expect(global).toHaveTextContent("Elevada (ELEVATED)");
    expect(global).toHaveTextContent("44 / 120");
  });

  it("renders the bulkhead and the open circuit from the snapshot", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    const circuit = await screen.findByTestId("capacity-circuit-WORKER_TYPE:CALLBACK_DELIVERY");
    expect(circuit).toHaveTextContent("Aberto (OPEN)");
    expect(circuit).toHaveTextContent("5 falha(s)");

    const bulkhead = screen.getByTestId("capacity-bulkhead-WORKER_TYPE:CALLBACK_DELIVERY");
    expect(bulkhead).toHaveTextContent("Saturado (SATURATED)");
    expect(bulkhead).toHaveTextContent("4 / 4");
  });

  it("lists shedding decisions with result, reason code and policy reference", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    const decision = await screen.findByTestId("capacity-decision-dec-1");
    expect(decision).toHaveTextContent("Descartado (SHED)");
    expect(decision).toHaveTextContent("BACKLOG_HARD_LIMIT");
    expect(decision).toHaveTextContent("capacity:worker:callback@1.0");
    expect(decision).toHaveTextContent("Limite rígido de fila");
  });

  it("hides the detail sections until the user opens them", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    await screen.findByTestId("capacity-mode");
    const resilience = screen.getByTestId("capacity-section-resilience");
    expect(resilience).toHaveAttribute("hidden");
    expect(screen.getByTestId("capacity-toggle-resilience")).toHaveAttribute(
      "aria-expanded",
      "false",
    );
    fireEvent.click(screen.getByTestId("capacity-toggle-resilience"));
    expect(screen.getByTestId("capacity-section-resilience")).not.toHaveAttribute("hidden");
  });

  it("loads more admission decisions on demand", async () => {
    stubSnapshot(snapshotFixture(), [
      {
        decisionId: "dec-2",
        decidedAt: new Date().toISOString(),
        result: "REJECTED_QUOTA",
        reasonCode: "QUOTA_EXHAUSTED",
        policyRef: "capacity:global@1.0",
        policyVersion: "1.0",
        scopeType: "GLOBAL",
        scopeRef: "GLOBAL",
        shedReason: "QUOTA_EXHAUSTED",
        monitorOnly: false,
      },
    ]);
    render(<CapacityResilience />);
    fireEvent.click(await screen.findByTestId("capacity-load-decisions"));
    await waitFor(() =>
      expect(screen.getByTestId("capacity-decision-dec-2")).toHaveTextContent(
        "Recusado por cota (REJECTED_QUOTA)",
      ),
    );
    const call = fetch.mock.calls.find((entry) => String(entry[0]).includes("/decisions"));
    expect(call[0]).toBe("/v1/console/capacity/decisions?limit=50");
  });

  it("shows a safe message when the decision log is unavailable", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    fireEvent.click(await screen.findByTestId("capacity-load-decisions"));
    await waitFor(() =>
      expect(screen.getByTestId("capacity-decisions-error")).toHaveTextContent(
        /indisponível ou não autorizado/i,
      ),
    );
  });

  it("shows the disabled state when the capability responds 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Not Found", status: 404 }, 404)),
    );
    render(<CapacityResilience />);
    await waitFor(() => expect(screen.getByTestId("capacity-disabled")).toBeInTheDocument());
    expect(screen.queryByTestId("capacity-pressure")).not.toBeInTheDocument();
    expect(screen.queryByTestId("capacity-executive")).not.toBeInTheDocument();
  });

  it("shows the disabled state when the module reports DISABLED", async () => {
    stubSnapshot(
      snapshotFixture({
        mode: "DISABLED",
        policies: [],
        pressure: [],
        bulkheads: [],
        circuits: [],
        recentDecisions: [],
      }),
    );
    render(<CapacityResilience />);
    await waitFor(() => expect(screen.getByTestId("capacity-disabled")).toBeInTheDocument());
    expect(screen.queryByTestId("capacity-executive")).not.toBeInTheDocument();
  });

  it("shows the unauthorized state when the credential is rejected", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Forbidden", status: 403 }, 403)),
    );
    render(<CapacityResilience />);
    await waitFor(() => expect(screen.getByTestId("capacity-unauthorized")).toBeInTheDocument());
  });

  it("shows the empty state without treating it as available capacity", async () => {
    stubSnapshot(
      snapshotFixture({
        mode: "MONITOR_ONLY",
        policies: [],
        pressure: [],
        bulkheads: [],
        circuits: [],
        recentDecisions: [],
      }),
    );
    render(<CapacityResilience />);
    await waitFor(() => expect(screen.getByTestId("capacity-empty")).toBeInTheDocument());
    expect(screen.getByTestId("capacity-empty")).toHaveTextContent(/não é lida como folga/i);
  });

  it("flags an aged reading instead of presenting it as current", async () => {
    const old = new Date(Date.now() - STALE_AFTER_MS - 120_000).toISOString();
    stubSnapshot(snapshotFixture({ calculatedAt: old }));
    render(<CapacityResilience />);
    await waitFor(() => expect(screen.getByTestId("capacity-stale")).toBeInTheDocument());
    expect(screen.getByTestId("capacity-stale")).toHaveTextContent(/envelhecida/i);
  });

  it("surfaces a transport error instead of an optimistic reading", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => jsonResponse({ title: "Internal Server Error", status: 500 }, 500)),
    );
    render(<CapacityResilience />);
    await waitFor(() => expect(screen.getByTestId("capacity-error")).toBeInTheDocument());
  });

  it("reports partial data quality instead of assuming capacity is free", async () => {
    stubSnapshot(
      snapshotFixture({
        dataQuality: {
          schemaVersion: 1,
          complete: false,
          resultLimitReached: true,
          availableSources: ["capacityPolicyCatalog"],
          missingSources: ["workerBacklogStore"],
          warnings: ["Admission decision log truncated at maxSize=200"],
        },
      }),
    );
    render(<CapacityResilience />);
    const partial = await screen.findByTestId("capacity-partial");
    expect(partial).toHaveTextContent("workerBacklogStore");
    expect(partial).toHaveTextContent("maxSize=200");
  });

  it("refetches the snapshot when the refresh button is used", async () => {
    stubSnapshot();
    render(<CapacityResilience />);
    await screen.findByTestId("capacity-mode");
    const before = fetch.mock.calls.length;
    fireEvent.click(screen.getByTestId("capacity-refresh"));
    await waitFor(() => expect(fetch.mock.calls.length).toBeGreaterThan(before));
  });

  it("does not claim production throughput, SLAs or capacity guarantees", async () => {
    stubSnapshot();
    const { container } = render(<CapacityResilience />);
    await screen.findByTestId("capacity-pressure");
    const text = container.textContent;
    expect(text).toContain("SEM CAPACIDADE PRODUTIVA AFERIDA");
    expect(text).not.toMatch(/\bSLA\b/);
    expect(text).not.toMatch(/\bSLO\b/);
    expect(text).not.toMatch(/pronto para produç[ãa]o/i);
    expect(text).not.toMatch(/production[- ]ready/i);
    expect(text).not.toMatch(/em produç[ãa]o/i);
    expect(text).not.toMatch(/\b\d+([.,]\d+)?\s*(req|reqs|rps|tps|qps)\b/i);
    expect(text).not.toMatch(/\b\d+([.,]\d+)?\s*(req|transaç[õo]es|chamadas)\s*\/\s*s/i);
    expect(text).not.toMatch(/throughput/i);
    expect(text).not.toMatch(/99[.,]9/);
  });
});
