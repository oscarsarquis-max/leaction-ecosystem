package br.com.banco.spider.operational.workers;

import br.com.banco.spider.operational.health.DataQualitySummary;
import java.time.Instant;
import java.util.List;

/**
 * Projeção segura do runtime de workers. A fronteira do runtime é simulada; as integrações
 * permanecem exclusivamente Mock.
 */
public record WorkerRuntimeSnapshot(
    int schemaVersion,
    Instant calculatedAt,
    String boundary,
    String integrationBoundary,
    WorkerRuntimeStatus runtimeStatus,
    List<WorkerInstance> workers,
    List<DurableSchedule> schedules,
    List<WorkerBacklogView> backlogs,
    int staleWorkers,
    int expiredLeases,
    Long oldestPendingAgeMs,
    DataQualitySummary dataQuality) {

  public static final int SCHEMA_VERSION = 1;
  public static final String BOUNDARY = "SIMULATED_INFRASTRUCTURE";
  public static final String INTEGRATION_BOUNDARY = "MOCK_ONLY";

  public WorkerRuntimeSnapshot {
    workers = workers == null ? List.of() : List.copyOf(workers);
    schedules = schedules == null ? List.of() : List.copyOf(schedules);
    backlogs = backlogs == null ? List.of() : List.copyOf(backlogs);
  }

  public static WorkerRuntimeSnapshot disabled(Instant calculatedAt) {
    return new WorkerRuntimeSnapshot(
        SCHEMA_VERSION,
        calculatedAt,
        BOUNDARY,
        INTEGRATION_BOUNDARY,
        WorkerRuntimeStatus.DISABLED,
        List.of(),
        List.of(),
        List.of(),
        0,
        0,
        null,
        new DataQualitySummary(
            1, true, false, List.of(), List.of(), List.of("Worker runtime disabled")));
  }
}
