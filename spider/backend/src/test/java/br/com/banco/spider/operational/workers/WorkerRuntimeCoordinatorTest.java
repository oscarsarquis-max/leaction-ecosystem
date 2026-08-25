package br.com.banco.spider.operational.workers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.WorkerRuntimeProperties;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryDurableScheduleStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryWorkerInstanceStore;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

class WorkerRuntimeCoordinatorTest {

  private static final WorkerType TYPE = WorkerType.SIGNAL_APPLICATION;

  private WorkerRuntimeTestSupport.MutableClock clock;
  private InMemoryDurableScheduleStore scheduleStore;
  private InMemoryWorkerInstanceStore instanceStore;
  private CountingHandler handler;
  private WorkerRuntimeCatalog catalog;
  private WorkerRuntimeProperties properties;
  private WorkerRuntimeCoordinator coordinator;
  private RequestWorkerDrainUseCase drainUseCase;

  @BeforeEach
  void startRuntime() {
    clock = new WorkerRuntimeTestSupport.MutableClock(Instant.parse("2026-08-25T12:00:00Z"));
    scheduleStore = new InMemoryDurableScheduleStore();
    instanceStore = new InMemoryWorkerInstanceStore();
    handler = new CountingHandler();
    catalog = WorkerRuntimeTestSupport.catalog();
    properties = WorkerRuntimeTestSupport.properties();
    WorkerRuntimeTelemetry telemetry = WorkerRuntimeTestSupport.silentTelemetry();
    WorkerScheduleRunner runner =
        new WorkerScheduleRunner(catalog, scheduleStore, instanceStore, telemetry, clock);
    drainUseCase = new RequestWorkerDrainUseCase(instanceStore, catalog, telemetry, clock);
    coordinator =
        new WorkerRuntimeCoordinator(
            properties,
            catalog,
            scheduleStore,
            instanceStore,
            runner,
            telemetry,
            clock,
            List.of(handler));
    coordinator.start();
  }

  @AfterEach
  void stopRuntime() {
    coordinator.stop();
  }

  @Test
  void startupSeedsOnlySchedulesWithHandlersAndRegistersOneWorkerPerType() {
    assertEquals(catalog.definitions().size(), scheduleStore.findAll().size());
    assertTrue(
        scheduleStore.findByCode(catalog.definition(TYPE).scheduleCode()).orElseThrow().enabled());
    assertFalse(
        scheduleStore
            .findByCode(catalog.definition(WorkerType.WAIT_EXPIRY).scheduleCode())
            .orElseThrow()
            .enabled(),
        "tipo sem handler registrado não deve ficar habilitado");

    List<WorkerInstance> workers = instanceStore.findAll();
    assertEquals(1, workers.size());
    assertEquals(TYPE, workers.getFirst().workerType());
    assertEquals(WorkerInstanceStatus.IDLE, workers.getFirst().status());
  }

  @Test
  void recoverySchedulesStayDisabledWhenRecoveryIsOff() {
    assertFalse(properties.getRecovery().isEnabled());
    assertFalse(
        scheduleStore
            .findByCode(catalog.definition(WorkerType.CALLBACK_RECOVERY).scheduleCode())
            .orElseThrow()
            .enabled());
  }

  @Test
  void cycleRunsHandlerAndReturnsWorkerToIdle() {
    Optional<ScheduleOutcome> outcome = coordinator.runOnceNow(TYPE);

    assertEquals(Optional.of(ScheduleOutcome.SUCCESS), outcome);
    assertEquals(1, handler.invocations.get());
    WorkerInstance worker = coordinator.workerFor(TYPE).orElseThrow();
    assertEquals(WorkerInstanceStatus.IDLE, worker.status());
    assertEquals(0, worker.currentClaims());
    assertEquals(1L, worker.processedCount());
  }

  @Test
  void scheduleIsNotEligibleAgainBeforeItsInterval() {
    assertTrue(coordinator.runOnceNow(TYPE).isPresent());
    assertTrue(coordinator.runOnceNow(TYPE).isEmpty(), "intervalo do agendamento deve ser respeitado");

    clock.advance(catalog.definition(TYPE).interval().plusSeconds(1));
    assertTrue(coordinator.runOnceNow(TYPE).isPresent());
    assertEquals(2, handler.invocations.get());
  }

  @Test
  void drainRequestStopsNewClaims() {
    assertTrue(coordinator.runOnceNow(TYPE).isPresent());
    String workerId = coordinator.workerFor(TYPE).orElseThrow().workerId();

    WorkerInstance draining = drainUseCase.requestDrain(workerId, "test").orElseThrow();
    assertEquals(WorkerInstanceStatus.DRAINING, draining.status());

    clock.advance(catalog.definition(TYPE).interval().plusSeconds(1));
    assertTrue(coordinator.runOnceNow(TYPE).isEmpty(), "worker em drenagem não assume trabalho novo");
    assertEquals(1, handler.invocations.get());
  }

  @Test
  void drainedWorkerIsStoppedByTheLoopWithoutHoldingTheSchedule() {
    String workerId = coordinator.workerFor(TYPE).orElseThrow().workerId();
    drainUseCase.requestDrain(workerId, "test");

    coordinator.tick();

    WorkerInstance stopped = instanceStore.findById(workerId).orElseThrow();
    assertEquals(WorkerInstanceStatus.STOPPED, stopped.status());
    assertEquals(
        null,
        scheduleStore
            .findByCode(catalog.definition(TYPE).scheduleCode())
            .orElseThrow()
            .ownerWorkerId(),
        "a drenagem não deve deixar posse pendurada no agendamento");
  }

  @Test
  void missingHeartbeatMarksWorkerStale() {
    String workerId = coordinator.workerFor(TYPE).orElseThrow().workerId();
    // Desliga o agendamento para que a batida observada seja apenas a detecção de sinal ausente.
    String scheduleCode = catalog.definition(TYPE).scheduleCode();
    scheduleStore.upsert(scheduleStore.findByCode(scheduleCode).orElseThrow().withEnabled(false));
    clock.advance(properties.getStaleAfter().plus(Duration.ofSeconds(5)));

    coordinator.tick();

    assertEquals(
        WorkerInstanceStatus.STALE, instanceStore.findById(workerId).orElseThrow().status());
  }

  @Test
  void handlerFailureIsCountedWithoutKillingTheWorker() {
    handler.fail = true;

    assertEquals(Optional.of(ScheduleOutcome.FAILED), coordinator.runOnceNow(TYPE));

    WorkerInstance worker = coordinator.workerFor(TYPE).orElseThrow();
    assertEquals(1L, worker.failureCount());
    assertEquals(WorkerInstanceStatus.IDLE, worker.status());
    assertEquals(
        ScheduleOutcome.FAILED,
        scheduleStore
            .findByCode(catalog.definition(TYPE).scheduleCode())
            .orElseThrow()
            .lastOutcome());
  }

  private static final class CountingHandler implements WorkerTypeHandler {
    private final AtomicInteger invocations = new AtomicInteger();
    private boolean fail;

    @Override
    public WorkerType workerType() {
      return TYPE;
    }

    @Override
    public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
      invocations.incrementAndGet();
      return fail
          ? Mono.error(new IllegalStateException("simulated handler failure"))
          : Mono.just(ScheduleOutcome.SUCCESS);
    }
  }
}
