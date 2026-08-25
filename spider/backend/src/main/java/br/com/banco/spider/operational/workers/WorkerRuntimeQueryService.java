package br.com.banco.spider.operational.workers;

import br.com.banco.spider.config.WorkerRuntimeProperties;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.health.DataQualitySummary;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;

/** Projeção de leitura do runtime de workers. Somente estado seguro; nada de conteúdo de negócio. */
public class WorkerRuntimeQueryService {

  private final WorkerRuntimeProperties properties;
  private final WorkerInstanceStorePort instanceStore;
  private final DurableScheduleStorePort scheduleStore;
  private final WorkerBacklogQueryService backlogService;
  private final SpiderClock clock;

  public WorkerRuntimeQueryService(
      WorkerRuntimeProperties properties,
      WorkerInstanceStorePort instanceStore,
      DurableScheduleStorePort scheduleStore,
      WorkerBacklogQueryService backlogService,
      SpiderClock clock) {
    this.properties = properties;
    this.instanceStore = instanceStore;
    this.scheduleStore = scheduleStore;
    this.backlogService = backlogService;
    this.clock = clock;
  }

  public boolean enabled() {
    return properties.isEnabled();
  }

  public WorkerRuntimeSnapshot getSnapshot() {
    Instant now = clock.now();
    if (!properties.isEnabled()) {
      return WorkerRuntimeSnapshot.disabled(now);
    }
    List<WorkerInstance> workers = instanceStore.findAll();
    List<DurableSchedule> schedules = scheduleStore.findAll();
    List<WorkerBacklogView> backlogs = backlogService.backlogs();

    int staleWorkers =
        (int) workers.stream().filter(w -> w.status() == WorkerInstanceStatus.STALE).count();
    int expiredLeases = (int) schedules.stream().filter(s -> s.leaseExpiredAt(now)).count();
    Long oldestPendingAgeMs =
        backlogs.stream()
            .map(WorkerBacklogView::oldestEligibleAgeMs)
            .filter(java.util.Objects::nonNull)
            .max(Long::compareTo)
            .orElse(null);

    List<String> missing = new ArrayList<>();
    for (WorkerBacklogView backlog : backlogs) {
      if (backlog.status() == WorkerBacklogStatus.UNKNOWN) {
        missing.add(backlog.workerType().name());
      }
    }
    boolean approximate = backlogs.stream().anyMatch(WorkerBacklogView::approximate);
    DataQualitySummary quality =
        new DataQualitySummary(
            1,
            missing.isEmpty() && !approximate,
            approximate,
            List.of("workerInstanceStore", "durableScheduleStore"),
            missing,
            approximate
                ? List.of("Backlog counts capped at maxScan=" + WorkerBacklogQueryService.MAX_SCAN)
                : List.of());

    return new WorkerRuntimeSnapshot(
        WorkerRuntimeSnapshot.SCHEMA_VERSION,
        now,
        WorkerRuntimeSnapshot.BOUNDARY,
        WorkerRuntimeSnapshot.INTEGRATION_BOUNDARY,
        runtimeStatus(workers, backlogs, staleWorkers, expiredLeases),
        workers,
        schedules,
        backlogs,
        staleWorkers,
        expiredLeases,
        oldestPendingAgeMs,
        quality);
  }

  public List<WorkerInstance> workers() {
    return instanceStore.findAll();
  }

  public Optional<WorkerInstance> worker(String workerId) {
    return instanceStore.findById(workerId);
  }

  public List<DurableSchedule> schedules() {
    return scheduleStore.findAll();
  }

  public List<WorkerBacklogView> backlogs() {
    return backlogService.backlogs();
  }

  private static WorkerRuntimeStatus runtimeStatus(
      List<WorkerInstance> workers,
      List<WorkerBacklogView> backlogs,
      int staleWorkers,
      int expiredLeases) {
    if (workers.isEmpty()) {
      return WorkerRuntimeStatus.UNKNOWN;
    }
    if (workers.stream().allMatch(w -> w.status() == WorkerInstanceStatus.STOPPED)) {
      return WorkerRuntimeStatus.STOPPED;
    }
    if (workers.stream().anyMatch(WorkerInstance::draining)) {
      return WorkerRuntimeStatus.DRAINING;
    }
    boolean degradedBacklog =
        backlogs.stream()
            .anyMatch(
                backlog ->
                    backlog.status() == WorkerBacklogStatus.ACCUMULATING
                        || backlog.status() == WorkerBacklogStatus.STALE);
    if (staleWorkers > 0 || expiredLeases > 0 || degradedBacklog) {
      return WorkerRuntimeStatus.DEGRADED;
    }
    return WorkerRuntimeStatus.HEALTHY;
  }
}
