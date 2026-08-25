package br.com.banco.spider.operational.workers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryDurableScheduleStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryWorkerInstanceStore;
import java.time.Instant;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/**
 * Fencing observado pelo caminho que o laboratório de falhas usa: o harness roda contra as mesmas
 * portas de armazenamento do runtime.
 */
class WorkerFencingIntegrationTest {

  private WorkerRuntimeTestSupport.MutableClock clock;
  private InMemoryDurableScheduleStore scheduleStore;
  private InMemoryWorkerInstanceStore instanceStore;
  private FailureLabWorkerHarness harness;

  @BeforeEach
  void wireHarness() {
    clock = new WorkerRuntimeTestSupport.MutableClock(Instant.parse("2026-08-25T12:00:00Z"));
    scheduleStore = new InMemoryDurableScheduleStore();
    instanceStore = new InMemoryWorkerInstanceStore();
    WorkerRuntimeCatalog catalog = WorkerRuntimeTestSupport.catalog();
    WorkerRuntimeTelemetry telemetry = WorkerRuntimeTestSupport.silentTelemetry();
    WorkerBacklogQueryService backlogService =
        new WorkerBacklogQueryService(
            catalog,
            clock,
            WorkerRuntimeTestSupport.provider(null),
            WorkerRuntimeTestSupport.provider(null),
            WorkerRuntimeTestSupport.provider(null),
            WorkerRuntimeTestSupport.provider(null),
            WorkerRuntimeTestSupport.provider(null));
    harness =
        new FailureLabWorkerHarness(
            scheduleStore,
            instanceStore,
            backlogService,
            new RequestWorkerDrainUseCase(instanceStore, catalog, telemetry, clock),
            clock);
  }

  @Test
  void secondWorkerTakesOverAndLateCompletionFromTheFirstIsRejected() {
    Map<String, String> facts = harness.crashAfterClaim();

    assertEquals("ACQUIRED", facts.get("workerClaim"));
    assertEquals("EXPIRED", facts.get("workerLease"));
    assertEquals("ACQUIRED_AFTER_LEASE_EXPIRY", facts.get("workerReclaim"));
    assertEquals("STALE_COMPLETION_REJECTED", facts.get("workerFencing"));

    DurableSchedule current =
        scheduleStore.findByCode(FailureLabWorkerHarness.HARNESS_SCHEDULE_CODE).orElseThrow();
    assertEquals("lab:worker-b", current.ownerWorkerId());
    assertEquals(null, current.lastOutcome(), "a conclusão recusada não pode registrar desfecho");
  }

  @Test
  void onlyOneWorkerWinsTheSameSchedule() {
    Map<String, String> facts = harness.dualContention();

    assertEquals("SINGLE_WINNER", facts.get("workerContention"));
    DurableSchedule current =
        scheduleStore.findByCode(FailureLabWorkerHarness.HARNESS_SCHEDULE_CODE).orElseThrow();
    assertEquals(null, current.ownerWorkerId(), "o vencedor deve concluir e liberar a posse");
    assertEquals(ScheduleOutcome.SUCCESS, current.lastOutcome());
  }

  @Test
  void drainedWorkerReportsNoNewClaims() {
    Map<String, String> facts = harness.gracefulDrain();

    assertEquals("DRAINING", facts.get("workerDrain"));
    assertEquals("NO_NEW_CLAIMS", facts.get("workerDrainClaims"));
  }

  @Test
  void completedScheduleKeepsItsNextEligibilityAcrossReload() {
    Map<String, String> facts = harness.restartRecovery();

    assertEquals("SCHEDULE_STATE_SURVIVED", facts.get("workerRestart"));
  }

  @Test
  void backlogIsObservedWithoutSeedingArtificialWork() {
    Map<String, String> facts = harness.backlogAccumulation();

    assertEquals("NOT_SEEDED_READ_ONLY_OBSERVATION", facts.get("workerBacklogSeeded"));
    assertEquals(WorkerBacklogStatus.UNKNOWN.name(), facts.get("workerBacklog"));
  }

  @Test
  void harnessNeverTouchesRealCatalogSchedules() {
    harness.crashAfterClaim();
    harness.dualContention();
    harness.restartRecovery();

    assertEquals(1, scheduleStore.findAll().size());
    assertTrue(
        WorkerRuntimeCatalog.scheduleCode(WorkerType.SIGNAL_APPLICATION)
            .equals("sched:signal-application@1"));
    assertFalse(
        scheduleStore
            .findByCode(WorkerRuntimeCatalog.scheduleCode(WorkerType.SIGNAL_APPLICATION))
            .isPresent(),
        "o harness não deve criar nem alterar agendamentos do catálogo real");
  }
}
