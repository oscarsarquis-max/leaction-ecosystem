package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.operational.health.DataQualitySummary;
import java.time.Instant;
import java.util.List;

/**
 * Projeção segura do governo de capacidade. A fronteira do módulo é simulada; as integrações
 * permanecem exclusivamente Mock.
 */
public record CapacityRuntimeSnapshot(
    int schemaVersion,
    Instant calculatedAt,
    String boundary,
    String integrationBoundary,
    CapacityMode mode,
    List<CapacityPolicy> policies,
    List<PressureSnapshot> pressure,
    List<BulkheadState> bulkheads,
    List<CircuitState> circuits,
    List<AdmissionDecision> recentDecisions,
    DataQualitySummary dataQuality) {

  public static final int SCHEMA_VERSION = 1;
  public static final String BOUNDARY = "SIMULATED_INFRASTRUCTURE";
  public static final String INTEGRATION_BOUNDARY = "MOCK_ONLY";

  public CapacityRuntimeSnapshot {
    policies = policies == null ? List.of() : List.copyOf(policies);
    pressure = pressure == null ? List.of() : List.copyOf(pressure);
    bulkheads = bulkheads == null ? List.of() : List.copyOf(bulkheads);
    circuits = circuits == null ? List.of() : List.copyOf(circuits);
    recentDecisions = recentDecisions == null ? List.of() : List.copyOf(recentDecisions);
  }

  public static CapacityRuntimeSnapshot disabled(Instant calculatedAt) {
    return new CapacityRuntimeSnapshot(
        SCHEMA_VERSION,
        calculatedAt,
        BOUNDARY,
        INTEGRATION_BOUNDARY,
        CapacityMode.DISABLED,
        List.of(),
        List.of(),
        List.of(),
        List.of(),
        List.of(),
        new DataQualitySummary(
            1, true, false, List.of(), List.of(), List.of("Capacity governance disabled")));
  }
}
