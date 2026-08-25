package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.config.CapacityProperties;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.health.DataQualitySummary;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;

/** Projeção de leitura do governo de capacidade. Somente estado seguro e contagens. */
public class CapacityQueryService {

  private final CapacityProperties properties;
  private final CapacityPolicyCatalog catalog;
  private final CapacityPressureService pressureService;
  private final BulkheadService bulkheads;
  private final CircuitBreakerService circuits;
  private final CapacityDecisionStore decisions;
  private final SpiderClock clock;

  public CapacityQueryService(
      CapacityProperties properties,
      CapacityPolicyCatalog catalog,
      CapacityPressureService pressureService,
      BulkheadService bulkheads,
      CircuitBreakerService circuits,
      CapacityDecisionStore decisions,
      SpiderClock clock) {
    this.properties = properties;
    this.catalog = catalog;
    this.pressureService = pressureService;
    this.bulkheads = bulkheads;
    this.circuits = circuits;
    this.decisions = decisions;
    this.clock = clock;
  }

  public boolean enabled() {
    return properties.isEnabled();
  }

  public CapacityMode mode() {
    if (!properties.isEnabled()) {
      return CapacityMode.DISABLED;
    }
    return properties.getEnforcement().isEnabled()
        ? CapacityMode.ENFORCED
        : CapacityMode.MONITOR_ONLY;
  }

  public CapacityRuntimeSnapshot getSnapshot() {
    Instant now = clock.now();
    if (!properties.isEnabled()) {
      return CapacityRuntimeSnapshot.disabled(now);
    }
    List<PressureSnapshot> pressure = pressureService.pressure();
    boolean anyUnknown =
        pressure.stream().anyMatch(item -> item.level() == CapacityPressureLevel.UNKNOWN);

    List<String> warnings = new ArrayList<>();
    warnings.add(
        "Bulkheads, circuits, quotas and admission decisions are in-memory: the reading restarts"
            + " empty after a process restart.");
    if (decisions.truncated()) {
      warnings.add("Admission decision log truncated at maxSize=" + decisions.maxSize());
    }
    List<String> missing = new ArrayList<>();
    if (anyUnknown) {
      missing.add("workerBacklogStore");
    }
    DataQualitySummary quality =
        new DataQualitySummary(
            1,
            false,
            decisions.truncated(),
            List.of("capacityPolicyCatalog", "capacityRuntimeState"),
            missing,
            warnings);

    return new CapacityRuntimeSnapshot(
        CapacityRuntimeSnapshot.SCHEMA_VERSION,
        now,
        CapacityRuntimeSnapshot.BOUNDARY,
        CapacityRuntimeSnapshot.INTEGRATION_BOUNDARY,
        mode(),
        catalog.policies(),
        pressure,
        bulkheads.states(),
        circuits.states(),
        decisions.recent(0),
        quality);
  }

  public List<CapacityPolicy> policies() {
    return catalog.policies();
  }

  public List<PressureSnapshot> pressure() {
    return pressureService.pressure();
  }

  public List<BulkheadState> bulkheads() {
    return bulkheads.states();
  }

  public List<CircuitState> circuits() {
    return circuits.states();
  }

  public List<AdmissionDecision> decisions(int limit) {
    return decisions.recent(limit);
  }
}
