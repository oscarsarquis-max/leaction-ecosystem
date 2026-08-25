package br.com.banco.spider.operational.workers;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryDurableScheduleStore;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class DurableScheduleStoreCasTest {

  private static final Instant NOW = Instant.parse("2026-08-25T12:00:00Z");
  private static final Duration LEASE = Duration.ofSeconds(30);

  private final WorkerRuntimeCatalog catalog = WorkerRuntimeTestSupport.catalog();
  private InMemoryDurableScheduleStore store;
  private String scheduleCode;

  @BeforeEach
  void seedCatalog() {
    store = new InMemoryDurableScheduleStore();
    store.seed(
        catalog.definitions().stream()
            .map(definition -> DurableSchedule.seed(definition, true, NOW))
            .toList());
    scheduleCode = catalog.definition(WorkerType.SIGNAL_APPLICATION).scheduleCode();
  }

  @Test
  void seedIsIdempotentAndNeverOverwritesExistingRow() {
    assertEquals(catalog.definitions().size(), store.findAll().size());
    DurableSchedule claimed =
        store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();

    store.seed(
        List.of(DurableSchedule.seed(catalog.definition(WorkerType.SIGNAL_APPLICATION), true, NOW)));

    DurableSchedule current = store.findByCode(scheduleCode).orElseThrow();
    assertEquals(claimed.version(), current.version());
    assertEquals("worker-a", current.ownerWorkerId());
  }

  @Test
  void claimRequiresMatchingVersion() {
    assertTrue(store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).isPresent());
    assertTrue(
        store.tryClaim(scheduleCode, 0L, "worker-b", NOW, NOW.plus(LEASE)).isEmpty(),
        "versão obsoleta não pode vencer o claim");
  }

  @Test
  void onlyOneOfTwoConcurrentClaimsWins() {
    long observedVersion = store.findByCode(scheduleCode).orElseThrow().version();
    Optional<DurableSchedule> first =
        store.tryClaim(scheduleCode, observedVersion, "worker-a", NOW, NOW.plus(LEASE));
    Optional<DurableSchedule> second =
        store.tryClaim(scheduleCode, observedVersion, "worker-b", NOW, NOW.plus(LEASE));

    assertTrue(first.isPresent());
    assertTrue(second.isEmpty());
    assertEquals(1L, first.get().fencingToken());
  }

  @Test
  void claimIsRejectedWhileLeaseIsHeldByAnotherWorker() {
    DurableSchedule claimed =
        store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    assertTrue(
        store
            .tryClaim(scheduleCode, claimed.version(), "worker-b", NOW, NOW.plus(LEASE))
            .isEmpty());
  }

  @Test
  void expiredLeaseAllowsAnotherWorkerAndRaisesFencing() {
    DurableSchedule first =
        store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    store.simulateLeaseExpiry(scheduleCode, NOW.minusSeconds(1));
    DurableSchedule expired = store.findByCode(scheduleCode).orElseThrow();
    assertTrue(expired.leaseExpiredAt(NOW));

    DurableSchedule second =
        store
            .tryClaim(scheduleCode, expired.version(), "worker-b", NOW, NOW.plus(LEASE))
            .orElseThrow();

    assertEquals("worker-b", second.ownerWorkerId());
    assertTrue(second.fencingToken() > first.fencingToken());
  }

  @Test
  void completionFromSupersededOwnerIsRejected() {
    DurableSchedule first =
        store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    store.simulateLeaseExpiry(scheduleCode, NOW.minusSeconds(1));
    DurableSchedule expired = store.findByCode(scheduleCode).orElseThrow();
    store.tryClaim(scheduleCode, expired.version(), "worker-b", NOW, NOW.plus(LEASE)).orElseThrow();

    assertFalse(
        store.complete(
            scheduleCode,
            "worker-a",
            first.fencingToken(),
            NOW,
            ScheduleOutcome.SUCCESS,
            NOW.plusSeconds(2)),
        "dono superado não pode concluir o ciclo do dono atual");
    assertFalse(store.isCurrentOwner(scheduleCode, "worker-a", first.fencingToken()));
    assertEquals("worker-b", store.findByCode(scheduleCode).orElseThrow().ownerWorkerId());
  }

  @Test
  void completionClearsOwnershipAndSchedulesNextEligibility() {
    DurableSchedule claimed =
        store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    Instant next = NOW.plusSeconds(2);

    assertTrue(
        store.complete(
            scheduleCode, "worker-a", claimed.fencingToken(), NOW, ScheduleOutcome.SUCCESS, next));

    DurableSchedule completed = store.findByCode(scheduleCode).orElseThrow();
    assertEquals(null, completed.ownerWorkerId());
    assertEquals(null, completed.leaseUntil());
    assertEquals(ScheduleOutcome.SUCCESS, completed.lastOutcome());
    assertEquals(next, completed.nextEligibleAt());
    assertFalse(completed.eligibleAt(NOW));
    assertTrue(completed.eligibleAt(next));
  }

  @Test
  void disabledScheduleIsNeverEligibleOrClaimable() {
    DurableSchedule disabled = store.findByCode(scheduleCode).orElseThrow().withEnabled(false);
    store.upsert(disabled);

    assertTrue(store.findEligible(NOW, 10).stream().noneMatch(s -> s.scheduleCode().equals(scheduleCode)));
    assertTrue(
        store.tryClaim(scheduleCode, disabled.version(), "worker-a", NOW, NOW.plus(LEASE)).isEmpty());
  }

  @Test
  void findEligibleSkipsSchedulesWithActiveLease() {
    store.tryClaim(scheduleCode, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    assertTrue(
        store.findEligible(NOW, 20).stream()
            .noneMatch(schedule -> schedule.scheduleCode().equals(scheduleCode)));
  }
}
