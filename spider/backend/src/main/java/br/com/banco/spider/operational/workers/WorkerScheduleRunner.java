package br.com.banco.spider.operational.workers;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.capacity.AdmissionDecision;
import br.com.banco.spider.operational.capacity.AdmissionRequest;
import br.com.banco.spider.operational.capacity.BulkheadAcquisition;
import br.com.banco.spider.operational.capacity.BulkheadService;
import br.com.banco.spider.operational.capacity.CapacityAdmissionService;
import br.com.banco.spider.operational.capacity.ShedReason;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Duration;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Executa um ciclo completo de um agendamento: admissão, claim, execução do processador e conclusão
 * com fencing.
 *
 * <p>Os processadores canônicos são reativos. Este runner é invocado sempre a partir de uma thread
 * do {@code ScheduledExecutorService} do runtime — nunca de uma thread de event-loop do Reactor
 * Netty — por isso o {@code block(executionTimeout)} é seguro aqui e não bloquearia o servidor
 * reativo.
 *
 * <p>A admissão de capacidade, quando presente, decide <em>antes</em> do {@code tryClaim}. Isso não é
 * detalhe de ordem: um claim recusado depois de acontecer já teria incrementado o token de fencing e
 * a versão do agendamento, e cada recusa acabaria queimando posse sem trabalho executado.
 */
public class WorkerScheduleRunner {

  private static final Logger log = LoggerFactory.getLogger(WorkerScheduleRunner.class);

  private final WorkerRuntimeCatalog catalog;
  private final DurableScheduleStorePort scheduleStore;
  private final WorkerInstanceStorePort instanceStore;
  private final WorkerRuntimeTelemetry telemetry;
  private final SpiderClock clock;
  private final ObjectProvider<CapacityAdmissionService> admissionProvider;
  private final ObjectProvider<BulkheadService> bulkheadProvider;

  public WorkerScheduleRunner(
      WorkerRuntimeCatalog catalog,
      DurableScheduleStorePort scheduleStore,
      WorkerInstanceStorePort instanceStore,
      WorkerRuntimeTelemetry telemetry,
      SpiderClock clock) {
    this(catalog, scheduleStore, instanceStore, telemetry, clock, absent(), absent());
  }

  public WorkerScheduleRunner(
      WorkerRuntimeCatalog catalog,
      DurableScheduleStorePort scheduleStore,
      WorkerInstanceStorePort instanceStore,
      WorkerRuntimeTelemetry telemetry,
      SpiderClock clock,
      ObjectProvider<CapacityAdmissionService> admissionProvider,
      ObjectProvider<BulkheadService> bulkheadProvider) {
    this.catalog = catalog;
    this.scheduleStore = scheduleStore;
    this.instanceStore = instanceStore;
    this.telemetry = telemetry;
    this.clock = clock;
    this.admissionProvider = admissionProvider;
    this.bulkheadProvider = bulkheadProvider;
  }

  /** Retorna vazio quando não havia trabalho elegível ou o claim foi perdido para outro worker. */
  public Optional<ScheduleOutcome> runOnce(WorkerInstance worker, WorkerTypeHandler handler) {
    WorkerTypeDefinition definition = catalog.definition(worker.workerType());
    Instant now = clock.now();
    Optional<DurableSchedule> current = scheduleStore.findByCode(definition.scheduleCode());
    if (current.isEmpty() || !current.get().eligibleAt(now) || current.get().leaseHeldAt(now)) {
      return Optional.empty();
    }

    CapacityAdmissionService admission = admissionProvider.getIfAvailable();
    AdmissionDecision decision = null;
    String reservedScopeKey = null;
    if (admission != null) {
      decision = admission.evaluate(admissionRequest(worker, definition, now));
      if (!decision.allowsWork()) {
        telemetry.emit(
            OperationalEventType.CAPACITY_ADMISSION_REJECTED,
            worker.workerType(),
            definition.scheduleCode(),
            decision.reasonCode(),
            OperationalEventOutcome.REJECTED,
            null);
        return Optional.empty();
      }
      if (!decision.monitorOnly()) {
        BulkheadService bulkheads = bulkheadProvider.getIfAvailable();
        if (bulkheads != null) {
          BulkheadAcquisition acquisition = bulkheads.acquire(decision.scopeKey());
          if (acquisition == BulkheadAcquisition.SATURATED) {
            admission.recordShed(decision, ShedReason.CONCURRENCY_EXHAUSTED);
            telemetry.emit(
                OperationalEventType.CAPACITY_ADMISSION_SHED,
                worker.workerType(),
                definition.scheduleCode(),
                ShedReason.CONCURRENCY_EXHAUSTED.name(),
                OperationalEventOutcome.REJECTED,
                null);
            return Optional.empty();
          }
          if (acquisition.held()) {
            reservedScopeKey = decision.scopeKey();
          }
        }
      }
    }

    try {
      return runClaimedCycle(
          worker, handler, definition, current.get().version(), now, admission, decision);
    } finally {
      if (reservedScopeKey != null) {
        BulkheadService bulkheads = bulkheadProvider.getIfAvailable();
        if (bulkheads != null) {
          bulkheads.release(reservedScopeKey);
        }
      }
    }
  }

  private Optional<ScheduleOutcome> runClaimedCycle(
      WorkerInstance worker,
      WorkerTypeHandler handler,
      WorkerTypeDefinition definition,
      long observedVersion,
      Instant now,
      CapacityAdmissionService admission,
      AdmissionDecision decision) {
    Optional<DurableSchedule> claimed =
        scheduleStore.tryClaim(
            definition.scheduleCode(),
            observedVersion,
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
    ScheduleOutcome settled = finalizeCycle(worker, definition, claim, outcome, now, finishedAt);
    recordCircuitOutcome(admission, decision, settled);
    return Optional.of(settled);
  }

  /**
   * O disjuntor só reage a falha técnica. {@code SKIPPED} é neutro — não havia trabalho — e
   * {@code FENCED_OUT} também, porque perder a posse é disputa saudável, não indisponibilidade.
   */
  private void recordCircuitOutcome(
      CapacityAdmissionService admission, AdmissionDecision decision, ScheduleOutcome outcome) {
    if (admission == null || decision == null) {
      return;
    }
    if (outcome == ScheduleOutcome.SKIPPED || outcome == ScheduleOutcome.FENCED_OUT) {
      return;
    }
    admission.recordOutcome(decision, outcome == ScheduleOutcome.FAILED);
  }

  private AdmissionRequest admissionRequest(
      WorkerInstance worker, WorkerTypeDefinition definition, Instant now) {
    return AdmissionRequest.forWorkerSchedule(
        worker.workerType().name(), definition.scheduleCode(), now, worker.workerId());
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

  /** Provider vazio para o wiring sem capacidade — mantém o runner idêntico ao de 019. */
  private static <T> ObjectProvider<T> absent() {
    return new ObjectProvider<>() {
      @Override
      public T getObject() {
        throw new IllegalStateException("no capacity bean available");
      }

      @Override
      public T getObject(Object... args) {
        return getObject();
      }

      @Override
      public T getIfAvailable() {
        return null;
      }

      @Override
      public T getIfUnique() {
        return null;
      }
    };
  }
}
