package br.com.banco.spider.operational.workers;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Executa um ciclo completo de um agendamento: claim, execução do processador e conclusão com
 * fencing.
 *
 * <p>Os processadores canônicos são reativos. Este runner é invocado sempre a partir de uma thread
 * do {@code ScheduledExecutorService} do runtime — nunca de uma thread de event-loop do Reactor
 * Netty — por isso o {@code block(executionTimeout)} é seguro aqui e não bloquearia o servidor
 * reativo.
 */
public class WorkerScheduleRunner {

  private static final Logger log = LoggerFactory.getLogger(WorkerScheduleRunner.class);

  private final WorkerRuntimeCatalog catalog;
  private final DurableScheduleStorePort scheduleStore;
  private final WorkerInstanceStorePort instanceStore;
  private final WorkerRuntimeTelemetry telemetry;
  private final SpiderClock clock;

  public WorkerScheduleRunner(
      WorkerRuntimeCatalog catalog,
      DurableScheduleStorePort scheduleStore,
      WorkerInstanceStorePort instanceStore,
      WorkerRuntimeTelemetry telemetry,
      SpiderClock clock) {
    this.catalog = catalog;
    this.scheduleStore = scheduleStore;
    this.instanceStore = instanceStore;
    this.telemetry = telemetry;
    this.clock = clock;
  }

  /** Retorna vazio quando não havia trabalho elegível ou o claim foi perdido para outro worker. */
  public Optional<ScheduleOutcome> runOnce(WorkerInstance worker, WorkerTypeHandler handler) {
    WorkerTypeDefinition definition = catalog.definition(worker.workerType());
    Instant now = clock.now();
    Optional<DurableSchedule> current = scheduleStore.findByCode(definition.scheduleCode());
    if (current.isEmpty() || !current.get().eligibleAt(now) || current.get().leaseHeldAt(now)) {
      return Optional.empty();
    }
    Optional<DurableSchedule> claimed =
        scheduleStore.tryClaim(
            definition.scheduleCode(),
            current.get().version(),
            worker.workerId(),
            now,
            now.plus(definition.leaseDuration()));
    if (claimed.isEmpty()) {
      return Optional.empty();
    }
    WorkerClaim claim = WorkerClaim.of(claimed.get(), now);
    markRunning(worker, now);
    telemetry.emit(
        OperationalEventType.SCHEDULE_CLAIMED,
        worker.workerType(),
        definition.scheduleCode(),
        "CLAIM_ACQUIRED");

    ScheduleOutcome outcome = invoke(worker, handler, definition, now);
    Instant finishedAt = clock.now();
    return Optional.of(finalizeCycle(worker, definition, claim, outcome, now, finishedAt));
  }

  private ScheduleOutcome invoke(
      WorkerInstance worker,
      WorkerTypeHandler handler,
      WorkerTypeDefinition definition,
      Instant now) {
    try {
      ScheduleOutcome outcome =
          handler
              .execute(worker.workerId(), definition.batchSize(), now)
              .block(definition.executionTimeout());
      return outcome == null ? ScheduleOutcome.SKIPPED : outcome;
    } catch (RuntimeException failure) {
      log.warn(
          "event=worker_schedule_failed scheduleCode={} workerType={} reasonCode={}",
          definition.scheduleCode(),
          worker.workerType(),
          failure.getClass().getSimpleName());
      return ScheduleOutcome.FAILED;
    }
  }

  private ScheduleOutcome finalizeCycle(
      WorkerInstance worker,
      WorkerTypeDefinition definition,
      WorkerClaim claim,
      ScheduleOutcome outcome,
      Instant startedAt,
      Instant finishedAt) {
    boolean stillOwner =
        scheduleStore.isCurrentOwner(
            definition.scheduleCode(), worker.workerId(), claim.fencingToken());
    Long durationMs = Math.max(0L, Duration.between(startedAt, finishedAt).toMillis());
    if (!stillOwner) {
      telemetry.emit(
          OperationalEventType.WORK_ITEM_FENCED_OUT,
          worker.workerType(),
          definition.scheduleCode(),
          "FENCING_REJECTED_STALE_OWNER",
          OperationalEventOutcome.REJECTED,
          durationMs);
      updateCounters(worker, ScheduleOutcome.FENCED_OUT, finishedAt);
      return ScheduleOutcome.FENCED_OUT;
    }
    Instant nextEligibleAt = finishedAt.plus(definition.interval());
    boolean completed =
        scheduleStore.complete(
            definition.scheduleCode(),
            worker.workerId(),
            claim.fencingToken(),
            finishedAt,
            outcome,
            nextEligibleAt);
    if (!completed) {
      telemetry.emit(
          OperationalEventType.WORK_ITEM_FENCED_OUT,
          worker.workerType(),
          definition.scheduleCode(),
          "COMPLETION_REJECTED",
          OperationalEventOutcome.REJECTED,
          durationMs);
      updateCounters(worker, ScheduleOutcome.FENCED_OUT, finishedAt);
      return ScheduleOutcome.FENCED_OUT;
    }
    telemetry.emit(
        outcome == ScheduleOutcome.FAILED
            ? OperationalEventType.SCHEDULE_FAILED
            : OperationalEventType.SCHEDULE_COMPLETED,
        worker.workerType(),
        definition.scheduleCode(),
        outcome.name(),
        outcome == ScheduleOutcome.FAILED
            ? OperationalEventOutcome.FAILURE
            : OperationalEventOutcome.SUCCESS,
        durationMs);
    updateCounters(worker, outcome, finishedAt);
    return outcome;
  }

  private void markRunning(WorkerInstance worker, Instant now) {
    instanceStore
        .findById(worker.workerId())
        .ifPresent(
            current -> {
              WorkerInstance running =
                  current.draining()
                      ? current.withHeartbeat(now).withClaims(1)
                      : current
                          .withStatus(WorkerInstanceStatus.RUNNING, now)
                          .withHeartbeat(now)
                          .withClaims(1);
              instanceStore.upsert(running);
            });
  }

  private void updateCounters(WorkerInstance worker, ScheduleOutcome outcome, Instant now) {
    instanceStore
        .findById(worker.workerId())
        .ifPresent(
            current -> {
              boolean failed =
                  outcome == ScheduleOutcome.FAILED || outcome == ScheduleOutcome.FENCED_OUT;
              WorkerInstance updated =
                  current
                      .withCounters(failed ? 0 : 1, failed ? 1 : 0)
                      .withClaims(0)
                      .withHeartbeat(now);
              if (updated.status() == WorkerInstanceStatus.RUNNING
                  || updated.status() == WorkerInstanceStatus.STARTING) {
                updated = updated.withStatus(WorkerInstanceStatus.IDLE, now);
              }
              instanceStore.upsert(updated);
            });
  }
}
