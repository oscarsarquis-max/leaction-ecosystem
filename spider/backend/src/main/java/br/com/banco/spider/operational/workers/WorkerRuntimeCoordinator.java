package br.com.banco.spider.operational.workers;

import br.com.banco.spider.config.WorkerRuntimeProperties;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import java.util.concurrent.RejectedExecutionException;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.ThreadFactory;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.SmartLifecycle;

/**
 * Laço durável do runtime de workers. Cada tipo de worker ganha uma instância própria — assim o
 * estado de drain e as contagens são legíveis por tipo — e todo trabalho roda em um pool limitado,
 * fora das threads reativas do servidor.
 */
public class WorkerRuntimeCoordinator implements SmartLifecycle {

  private static final Logger log = LoggerFactory.getLogger(WorkerRuntimeCoordinator.class);

  private final WorkerRuntimeProperties properties;
  private final WorkerRuntimeCatalog catalog;
  private final DurableScheduleStorePort scheduleStore;
  private final WorkerInstanceStorePort instanceStore;
  private final WorkerScheduleRunner runner;
  private final WorkerRuntimeTelemetry telemetry;
  private final SpiderClock clock;
  private final Map<WorkerType, WorkerTypeHandler> handlers = new EnumMap<>(WorkerType.class);
  private final Map<String, AtomicBoolean> inFlight = new ConcurrentHashMap<>();
  private final AtomicBoolean running = new AtomicBoolean(false);

  private volatile String runtimeInstanceId;
  private volatile ScheduledExecutorService scheduler;
  private volatile ScheduledFuture<?> tickHandle;

  public WorkerRuntimeCoordinator(
      WorkerRuntimeProperties properties,
      WorkerRuntimeCatalog catalog,
      DurableScheduleStorePort scheduleStore,
      WorkerInstanceStorePort instanceStore,
      WorkerScheduleRunner runner,
      WorkerRuntimeTelemetry telemetry,
      SpiderClock clock,
      List<WorkerTypeHandler> handlers) {
    this.properties = properties;
    this.catalog = catalog;
    this.scheduleStore = scheduleStore;
    this.instanceStore = instanceStore;
    this.runner = runner;
    this.telemetry = telemetry;
    this.clock = clock;
    for (WorkerTypeHandler handler : handlers) {
      this.handlers.put(handler.workerType(), handler);
    }
  }

  public String runtimeInstanceId() {
    return runtimeInstanceId;
  }

  public Map<WorkerType, WorkerTypeHandler> handlers() {
    return Map.copyOf(handlers);
  }

  @Override
  public void start() {
    if (!running.compareAndSet(false, true)) {
      return;
    }
    runtimeInstanceId =
        properties.getInstanceId() == null || properties.getInstanceId().isBlank()
            ? "wrk-inst-" + UUID.randomUUID()
            : properties.getInstanceId().trim();
    Instant now = clock.now();
    seedSchedules(now);
    registerWorkers(now);
    scheduler =
        Executors.newScheduledThreadPool(
            Math.max(1, properties.getMaxConcurrency()), threadFactory());
    long tickMillis = Math.max(50L, properties.getTickInterval().toMillis());
    tickHandle =
        scheduler.scheduleAtFixedRate(this::tickSafely, tickMillis, tickMillis, TimeUnit.MILLISECONDS);
    log.info(
        "event=worker_runtime_started runtimeInstanceId={} workerTypes={} boundary={}",
        runtimeInstanceId,
        handlers.keySet(),
        WorkerRuntimeSnapshot.BOUNDARY);
  }

  @Override
  public void stop() {
    if (!running.compareAndSet(true, false)) {
      return;
    }
    ScheduledFuture<?> handle = tickHandle;
    if (handle != null) {
      handle.cancel(false);
    }
    ScheduledExecutorService executor = scheduler;
    if (executor != null) {
      executor.shutdownNow();
    }
    Instant now = clock.now();
    for (WorkerInstance worker : instanceStore.findAll()) {
      if (!runtimeInstanceId.equals(worker.runtimeInstanceId())) {
        continue;
      }
      instanceStore.upsert(worker.withStatus(WorkerInstanceStatus.STOPPED, now));
      telemetry.emit(
          OperationalEventType.WORKER_STOPPED,
          worker.workerType(),
          catalog.definition(worker.workerType()).scheduleCode(),
          "RUNTIME_SHUTDOWN");
    }
    log.info("event=worker_runtime_stopped runtimeInstanceId={}", runtimeInstanceId);
  }

  @Override
  public boolean isRunning() {
    return running.get();
  }

  @Override
  public int getPhase() {
    return Integer.MAX_VALUE - 1000;
  }

  private void seedSchedules(Instant now) {
    List<DurableSchedule> seeds =
        catalog.definitions().stream()
            .map(definition -> DurableSchedule.seed(definition, enabledByPolicy(definition), now))
            .toList();
    scheduleStore.seed(seeds);
    // Reaplica a política de habilitação: um agendamento persistido de execução anterior não deve
    // continuar ligado quando a recuperação foi desligada por configuração.
    for (DurableSchedule seed : seeds) {
      scheduleStore
          .findByCode(seed.scheduleCode())
          .filter(existing -> existing.enabled() != seed.enabled())
          .ifPresent(existing -> scheduleStore.upsert(existing.withEnabled(seed.enabled())));
    }
  }

  private boolean enabledByPolicy(WorkerTypeDefinition definition) {
    if (!handlers.containsKey(definition.workerType())) {
      return false;
    }
    return !definition.workerType().recovery() || properties.getRecovery().isEnabled();
  }

  private void registerWorkers(Instant now) {
    for (WorkerTypeHandler handler : handlers.values()) {
      WorkerType type = handler.workerType();
      String workerId = workerId(type);
      WorkerInstance worker = WorkerInstance.starting(workerId, runtimeInstanceId, type, now);
      instanceStore.upsert(worker);
      inFlight.put(workerId, new AtomicBoolean(false));
      instanceStore.upsert(
          worker.withStatus(WorkerInstanceStatus.IDLE, now).withHeartbeat(now));
      telemetry.emit(
          OperationalEventType.WORKER_STARTED,
          type,
          catalog.definition(type).scheduleCode(),
          "WORKER_REGISTERED");
    }
  }

  private String workerId(WorkerType type) {
    return runtimeInstanceId + ":" + type.name().toLowerCase(java.util.Locale.ROOT);
  }

  private ThreadFactory threadFactory() {
    AtomicInteger sequence = new AtomicInteger();
    return task -> {
      Thread thread = new Thread(task, "spider-worker-runtime-" + sequence.incrementAndGet());
      thread.setDaemon(true);
      return thread;
    };
  }

  private void tickSafely() {
    try {
      tick();
    } catch (Throwable failure) {
      // O laço nunca morre por falha de um ciclo: a próxima batida tenta de novo.
      log.warn("event=worker_runtime_tick_failed reasonCode={}", failure.getClass().getSimpleName());
    }
  }

  /** Uma batida do laço. Visível para teste para permitir avanço determinístico. */
  public void tick() {
    Instant now = clock.now();
    markStaleWorkers(now);
    for (WorkerInstance worker : instanceStore.findAll()) {
      if (!runtimeInstanceId.equals(worker.runtimeInstanceId())) {
        continue;
      }
      if (worker.status() == WorkerInstanceStatus.STOPPED
          || worker.status() == WorkerInstanceStatus.FAILED) {
        continue;
      }
      instanceStore.upsert(worker.withHeartbeat(now));
      if (worker.draining()) {
        settleDrain(worker, now);
        continue;
      }
      dispatch(worker);
    }
  }

  private void markStaleWorkers(Instant now) {
    Instant staleBefore = now.minus(properties.getStaleAfter());
    for (WorkerInstance stale : instanceStore.findStale(staleBefore)) {
      instanceStore.upsert(stale.withStatus(WorkerInstanceStatus.STALE, now));
      telemetry.emit(
          OperationalEventType.LEASE_EXPIRED,
          stale.workerType(),
          catalog.definition(stale.workerType()).scheduleCode(),
          "HEARTBEAT_MISSED",
          OperationalEventOutcome.REJECTED,
          null);
    }
  }

  private void settleDrain(WorkerInstance worker, Instant now) {
    AtomicBoolean busy = inFlight.get(worker.workerId());
    boolean working = busy != null && busy.get();
    boolean ownsSchedule =
        scheduleStore
            .findByCode(catalog.definition(worker.workerType()).scheduleCode())
            .map(schedule -> worker.workerId().equals(schedule.ownerWorkerId()))
            .orElse(false);
    boolean timedOut =
        worker.drainRequestedAt() != null
            && !now.isBefore(worker.drainRequestedAt().plus(properties.getDrainTimeout()));
    if (working && !timedOut) {
      return;
    }
    if (ownsSchedule && !timedOut) {
      return;
    }
    if (worker.status() != WorkerInstanceStatus.STOPPED) {
      instanceStore.upsert(worker.withStatus(WorkerInstanceStatus.STOPPED, now).withClaims(0));
      telemetry.emit(
          OperationalEventType.WORKER_DRAINED,
          worker.workerType(),
          catalog.definition(worker.workerType()).scheduleCode(),
          timedOut ? "DRAIN_TIMEOUT" : "DRAIN_COMPLETE");
      telemetry.emit(
          OperationalEventType.WORKER_STOPPED,
          worker.workerType(),
          catalog.definition(worker.workerType()).scheduleCode(),
          "DRAINED");
    }
  }

  private void dispatch(WorkerInstance worker) {
    WorkerTypeHandler handler = handlers.get(worker.workerType());
    ScheduledExecutorService executor = scheduler;
    AtomicBoolean busy = inFlight.computeIfAbsent(worker.workerId(), key -> new AtomicBoolean(false));
    if (handler == null || executor == null || !busy.compareAndSet(false, true)) {
      return;
    }
    try {
      executor.execute(
          () -> {
            try {
              runner.runOnce(worker, handler);
            } catch (RuntimeException failure) {
              log.warn(
                  "event=worker_cycle_failed workerId={} reasonCode={}",
                  worker.workerId(),
                  failure.getClass().getSimpleName());
            } finally {
              busy.set(false);
            }
          });
    } catch (RejectedExecutionException rejected) {
      busy.set(false);
    }
  }

  /** Executa um ciclo síncrono do tipo informado — usado pelo laboratório de falhas e por testes. */
  public Optional<ScheduleOutcome> runOnceNow(WorkerType type) {
    WorkerTypeHandler handler = handlers.get(type);
    if (handler == null) {
      return Optional.empty();
    }
    return instanceStore
        .findById(workerId(type))
        .filter(worker -> !worker.draining())
        .flatMap(worker -> runner.runOnce(worker, handler));
  }

  public Optional<WorkerInstance> workerFor(WorkerType type) {
    return instanceStore.findById(workerId(type));
  }

  public Duration tickInterval() {
    return properties.getTickInterval();
  }
}
