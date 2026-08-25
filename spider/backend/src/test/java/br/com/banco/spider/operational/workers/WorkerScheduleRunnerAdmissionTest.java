package br.com.banco.spider.operational.workers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.CapacityProperties;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryDurableScheduleStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryWorkerInstanceStore;
import br.com.banco.spider.operational.capacity.AdmissionResult;
import br.com.banco.spider.operational.capacity.BulkheadService;
import br.com.banco.spider.operational.capacity.CapacityAdmissionService;
import br.com.banco.spider.operational.capacity.CapacityDecisionStore;
import br.com.banco.spider.operational.capacity.CapacityLimit;
import br.com.banco.spider.operational.capacity.CapacityPolicy;
import br.com.banco.spider.operational.capacity.CapacityPolicyCatalog;
import br.com.banco.spider.operational.capacity.CapacityPolicyState;
import br.com.banco.spider.operational.capacity.CapacityScopeType;
import br.com.banco.spider.operational.capacity.CapacityTelemetry;
import br.com.banco.spider.operational.capacity.CircuitBreakerService;
import br.com.banco.spider.operational.capacity.CircuitPhase;
import br.com.banco.spider.operational.capacity.QuotaService;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.core.publisher.Mono;

/**
 * A propriedade central de 020: a recusa de admissão acontece antes do claim, então uma rajada de
 * recusas não queima token de posse nem versão do agendamento durável.
 */
class WorkerScheduleRunnerAdmissionTest {

  private static final WorkerType TYPE = WorkerType.SIGNAL_APPLICATION;

  private WorkerRuntimeTestSupport.MutableClock clock;
  private InMemoryDurableScheduleStore scheduleStore;
  private InMemoryWorkerInstanceStore instanceStore;
  private WorkerRuntimeCatalog catalog;
  private WorkerTypeDefinition definition;
  private WorkerInstance worker;
  private CountingHandler handler;

  private BulkheadService bulkheads;
  private CircuitBreakerService circuits;
  private QuotaService quotas;
  private CapacityDecisionStore decisions;

  @BeforeEach
  void seedRuntime() {
    clock = new WorkerRuntimeTestSupport.MutableClock(Instant.parse("2026-08-25T12:00:00Z"));
    scheduleStore = new InMemoryDurableScheduleStore();
    instanceStore = new InMemoryWorkerInstanceStore();
    catalog = WorkerRuntimeTestSupport.catalog();
    definition = catalog.definition(TYPE);
    handler = new CountingHandler();

    scheduleStore.upsert(DurableSchedule.seed(definition, true, clock.now()));
    worker = WorkerInstance.starting("wrk-inst-admission:signal_application", "wrk-inst-admission", TYPE, clock.now());
    instanceStore.upsert(worker);

    bulkheads = new BulkheadService(clock);
    circuits = new CircuitBreakerService(clock, telemetry());
    quotas = new QuotaService(clock);
    decisions = new CapacityDecisionStore(CapacityDecisionStore.MAX_SIZE);
  }

  @Test
  void runnerWithoutCapacityBehavesExactlyAsBefore() {
    WorkerScheduleRunner runner = runner(null);

    assertEquals(Optional.of(ScheduleOutcome.SUCCESS), runner.runOnce(worker, handler));
    assertEquals(1, handler.invocations.get());
    assertEquals(1L, schedule().fencingToken());
  }

  @Test
  void rejectedAdmissionNeverClaimsAndKeepsTheFencingTokenIntact() {
    CapacityAdmissionService admission = admission(true, saturatedConcurrency());
    WorkerScheduleRunner runner = runner(admission);
    DurableSchedule before = schedule();

    Optional<ScheduleOutcome> outcome = runner.runOnce(worker, handler);

    assertTrue(outcome.isEmpty(), "a recusa não produz desfecho de ciclo");
    assertEquals(0, handler.invocations.get(), "o processador não pode ser invocado");
    DurableSchedule after = schedule();
    assertEquals(before.fencingToken(), after.fencingToken(), "a recusa não pode queimar posse");
    assertEquals(before.version(), after.version(), "a recusa não pode versionar o agendamento");
    assertEquals(null, after.ownerWorkerId());
    assertEquals(null, after.leaseUntil());
    assertEquals(
        AdmissionResult.REJECTED_CAPACITY, decisions.recent(1).getFirst().result());
  }

  @Test
  void repeatedRejectionsNeverAdvanceTheFencingToken() {
    CapacityAdmissionService admission = admission(true, saturatedConcurrency());
    WorkerScheduleRunner runner = runner(admission);
    long before = schedule().fencingToken();

    for (int attempt = 0; attempt < 25; attempt++) {
      assertTrue(runner.runOnce(worker, handler).isEmpty());
    }

    assertEquals(before, schedule().fencingToken());
    assertEquals(0, handler.invocations.get());
  }

  @Test
  void openCircuitRejectsBeforeTheClaimAsWell() {
    CapacityPolicy policy = circuitPolicy();
    circuits.recordFailure(policy.scopeKey(), policy);
    circuits.recordFailure(policy.scopeKey(), policy);
    assertEquals(CircuitPhase.OPEN, circuits.phase(policy.scopeKey()));
    WorkerScheduleRunner runner = runner(admission(true, List.of(policy)));
    long before = schedule().fencingToken();

    assertTrue(runner.runOnce(worker, handler).isEmpty());

    assertEquals(before, schedule().fencingToken());
    assertEquals(
        AdmissionResult.REJECTED_CIRCUIT_OPEN, decisions.recent(1).getFirst().result());
  }

  @Test
  void monitorOnlyModeRecordsTheIntentButRunsTheCycle() {
    WorkerScheduleRunner runner = runner(admission(false, saturatedConcurrency()));

    assertEquals(Optional.of(ScheduleOutcome.SUCCESS), runner.runOnce(worker, handler));

    assertEquals(1, handler.invocations.get());
    assertTrue(decisions.recent(1).getFirst().monitorOnly());
    assertEquals(AdmissionResult.ADMITTED, decisions.recent(1).getFirst().result());
  }

  @Test
  void admittedCycleReservesConcurrencyAndReleasesItAtTheEnd() {
    List<CapacityPolicy> policies = List.of(concurrencyPolicy(1));
    WorkerScheduleRunner runner = runner(admission(true, policies));

    assertEquals(Optional.of(ScheduleOutcome.SUCCESS), runner.runOnce(worker, handler));

    assertEquals(
        0,
        bulkheads.occupied(policies.getFirst().scopeKey()),
        "a vaga reservada precisa voltar ao fim do ciclo");
  }

  @Test
  void reservationIsReleasedEvenWhenTheHandlerFails() {
    List<CapacityPolicy> policies = List.of(concurrencyPolicy(1));
    WorkerScheduleRunner runner = runner(admission(true, policies));
    handler.fail = true;

    assertEquals(Optional.of(ScheduleOutcome.FAILED), runner.runOnce(worker, handler));

    assertEquals(0, bulkheads.occupied(policies.getFirst().scopeKey()));
  }

  @Test
  void technicalFailuresOfTheCycleOpenTheCircuitOfTheScope() {
    CapacityPolicy policy = circuitPolicy();
    WorkerScheduleRunner runner = runner(admission(true, List.of(policy)));
    handler.fail = true;

    assertEquals(Optional.of(ScheduleOutcome.FAILED), runner.runOnce(worker, handler));
    assertEquals(CircuitPhase.CLOSED, circuits.phase(policy.scopeKey()));

    clock.advance(definition.interval().plusSeconds(1));
    assertEquals(Optional.of(ScheduleOutcome.FAILED), runner.runOnce(worker, handler));

    assertEquals(CircuitPhase.OPEN, circuits.phase(policy.scopeKey()));
  }

  private DurableSchedule schedule() {
    return scheduleStore.findByCode(definition.scheduleCode()).orElseThrow();
  }

  private WorkerScheduleRunner runner(CapacityAdmissionService admission) {
    return new WorkerScheduleRunner(
        catalog,
        scheduleStore,
        instanceStore,
        WorkerRuntimeTestSupport.silentTelemetry(),
        clock,
        WorkerRuntimeTestSupport.provider(admission),
        WorkerRuntimeTestSupport.provider(admission == null ? null : bulkheads));
  }

  private CapacityAdmissionService admission(boolean enforcing, List<CapacityPolicy> policies) {
    CapacityProperties properties = new CapacityProperties();
    properties.setEnabled(true);
    properties.getEnforcement().setEnabled(enforcing);
    return new CapacityAdmissionService(
        properties,
        new CapacityPolicyCatalog(policies),
        bulkheads,
        circuits,
        quotas,
        decisions,
        telemetry(),
        clock,
        IdentifierGenerator.sequential("admission-test"),
        WorkerRuntimeTestSupport.provider(null));
  }

  /** Escopo já ocupado: a próxima avaliação encontra a concorrência esgotada. */
  private List<CapacityPolicy> saturatedConcurrency() {
    CapacityPolicy policy = concurrencyPolicy(1);
    bulkheads.register(policy.scopeKey(), 1);
    assertTrue(bulkheads.tryAcquire(policy.scopeKey(), 1));
    return List.of(policy);
  }

  private CapacityPolicy concurrencyPolicy(int maxConcurrency) {
    return policy(
        new CapacityLimit(
            maxConcurrency,
            CapacityLimit.NO_LIMIT,
            CapacityLimit.NO_LIMIT,
            0,
            Duration.ofMinutes(1),
            Duration.ZERO),
        0);
  }

  private CapacityPolicy circuitPolicy() {
    return policy(
        new CapacityLimit(
            0,
            CapacityLimit.NO_LIMIT,
            CapacityLimit.NO_LIMIT,
            0,
            Duration.ofMinutes(1),
            Duration.ZERO),
        2);
  }

  private CapacityPolicy policy(CapacityLimit limits, int circuitFailureThreshold) {
    return new CapacityPolicy(
        "capacity:test:runner",
        "1.0",
        CapacityScopeType.SCHEDULE,
        definition.scheduleCode(),
        CapacityPolicyState.ACTIVE,
        limits,
        circuitFailureThreshold,
        Duration.ofMinutes(1),
        Duration.ofMinutes(5),
        1,
        1,
        true);
  }

  private static CapacityTelemetry telemetry() {
    return new CapacityTelemetry(
        WorkerRuntimeTestSupport.provider((OperationalEventPublisher) null));
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
