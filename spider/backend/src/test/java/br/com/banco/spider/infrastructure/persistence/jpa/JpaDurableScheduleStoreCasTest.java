package br.com.banco.spider.infrastructure.persistence.jpa;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.RuntimeScheduleEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.RuntimeWorkerInstanceEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.RuntimeScheduleJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.RuntimeWorkerInstanceJpaRepository;
import br.com.banco.spider.operational.workers.DurableSchedule;
import br.com.banco.spider.operational.workers.DurableScheduleStorePort;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerInstance;
import br.com.banco.spider.operational.workers.WorkerInstanceStatus;
import br.com.banco.spider.operational.workers.WorkerInstanceStorePort;
import br.com.banco.spider.operational.workers.WorkerType;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.test.context.TestPropertySource;

/** CAS de claim, fencing e drenagem na persistência durável (JPA/H2). */
@DataJpaTest
@EntityScan(
    basePackageClasses = {RuntimeScheduleEntity.class, RuntimeWorkerInstanceEntity.class})
@EnableJpaRepositories(
    basePackageClasses = {
      RuntimeScheduleJpaRepository.class,
      RuntimeWorkerInstanceJpaRepository.class
    })
@TestPropertySource(
    properties = {
      "spring.datasource.url=jdbc:h2:mem:spider_runtime_datajpa;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class JpaDurableScheduleStoreCasTest {

  private static final Instant NOW = Instant.parse("2026-08-25T12:00:00Z");
  private static final Duration INTERVAL = Duration.ofSeconds(2);
  private static final Duration LEASE = Duration.ofSeconds(30);
  private static final String CODE = "sched:signal-application@1";

  @Autowired RuntimeScheduleJpaRepository scheduleRepo;
  @Autowired RuntimeWorkerInstanceJpaRepository instanceRepo;

  private DurableScheduleStorePort schedules;
  private WorkerInstanceStorePort instances;

  @BeforeEach
  void wireAdapters() {
    schedules = new JpaDurableScheduleStoreAdapter(scheduleRepo);
    instances = new JpaWorkerInstanceStoreAdapter(instanceRepo);
    schedules.seed(List.of(seed()));
  }

  @Test
  void seedIsIdempotent() {
    schedules.seed(List.of(seed()));
    assertEquals(1, schedules.findAll().size());
  }

  @Test
  void onlyOneWorkerWinsTheClaimFromTheSameObservedVersion() {
    long version = schedules.findByCode(CODE).orElseThrow().version();

    Optional<DurableSchedule> first =
        schedules.tryClaim(CODE, version, "worker-a", NOW, NOW.plus(LEASE));
    Optional<DurableSchedule> second =
        schedules.tryClaim(CODE, version, "worker-b", NOW, NOW.plus(LEASE));

    assertTrue(first.isPresent());
    assertTrue(second.isEmpty());
    assertEquals("worker-a", first.get().ownerWorkerId());
    assertEquals(1L, first.get().fencingToken());
  }

  @Test
  void heldLeaseBlocksAnotherWorkerUntilItExpires() {
    DurableSchedule claimed =
        schedules.tryClaim(CODE, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    assertTrue(schedules.tryClaim(CODE, claimed.version(), "worker-b", NOW, NOW.plus(LEASE)).isEmpty());

    schedules.simulateLeaseExpiry(CODE, NOW.minusSeconds(1));
    DurableSchedule expired = schedules.findByCode(CODE).orElseThrow();
    assertTrue(expired.leaseExpiredAt(NOW));

    DurableSchedule taken =
        schedules
            .tryClaim(CODE, expired.version(), "worker-b", NOW, NOW.plus(LEASE))
            .orElseThrow();
    assertEquals("worker-b", taken.ownerWorkerId());
    assertTrue(taken.fencingToken() > claimed.fencingToken());
  }

  @Test
  void completionFromASupersededOwnerIsRejected() {
    DurableSchedule first =
        schedules.tryClaim(CODE, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    schedules.simulateLeaseExpiry(CODE, NOW.minusSeconds(1));
    long version = schedules.findByCode(CODE).orElseThrow().version();
    schedules.tryClaim(CODE, version, "worker-b", NOW, NOW.plus(LEASE)).orElseThrow();

    assertFalse(
        schedules.complete(
            CODE, "worker-a", first.fencingToken(), NOW, ScheduleOutcome.SUCCESS, NOW.plus(INTERVAL)));
    assertFalse(schedules.isCurrentOwner(CODE, "worker-a", first.fencingToken()));
    assertNull(schedules.findByCode(CODE).orElseThrow().lastOutcome());
  }

  @Test
  void completionClearsTheLeaseAndSchedulesTheNextCycle() {
    DurableSchedule claimed =
        schedules.tryClaim(CODE, 0L, "worker-a", NOW, NOW.plus(LEASE)).orElseThrow();
    Instant next = NOW.plus(INTERVAL);

    assertTrue(
        schedules.complete(
            CODE, "worker-a", claimed.fencingToken(), NOW, ScheduleOutcome.SUCCESS, next));

    DurableSchedule completed = schedules.findByCode(CODE).orElseThrow();
    assertNull(completed.ownerWorkerId());
    assertNull(completed.leaseUntil());
    assertEquals(ScheduleOutcome.SUCCESS, completed.lastOutcome());
    assertEquals(next, completed.nextEligibleAt());
    assertTrue(schedules.findEligible(NOW, 10).isEmpty());
    assertFalse(schedules.findEligible(next, 10).isEmpty());
  }

  @Test
  void workerStatusTransitionUsesCompareAndSet() {
    WorkerInstance worker =
        instances.upsert(
            WorkerInstance.starting("wrk-1", "inst-1", WorkerType.SIGNAL_APPLICATION, NOW));

    assertTrue(
        instances
            .compareAndSetStatus(
                worker.workerId(), WorkerInstanceStatus.STARTING, WorkerInstanceStatus.IDLE, NOW)
            .isPresent());
    assertTrue(
        instances
            .compareAndSetStatus(
                worker.workerId(), WorkerInstanceStatus.STARTING, WorkerInstanceStatus.RUNNING, NOW)
            .isEmpty(),
        "transição a partir de estado antigo deve ser recusada");
    assertEquals(
        WorkerInstanceStatus.IDLE, instances.findById(worker.workerId()).orElseThrow().status());
  }

  @Test
  void staleWorkersAreFoundByHeartbeatWindow() {
    instances.upsert(
        WorkerInstance.starting("wrk-fresh", "inst-1", WorkerType.WAIT_EXPIRY, NOW)
            .withHeartbeat(NOW));
    instances.upsert(
        WorkerInstance.starting("wrk-old", "inst-1", WorkerType.CALLBACK_DELIVERY, NOW)
            .withHeartbeat(NOW.minusSeconds(60)));

    List<String> stale =
        instances.findStale(NOW.minusSeconds(30)).stream().map(WorkerInstance::workerId).toList();

    assertEquals(List.of("wrk-old"), stale);
  }

  private static DurableSchedule seed() {
    return new DurableSchedule(
        CODE, 0L, "1.0", WorkerType.SIGNAL_APPLICATION, true, INTERVAL, NOW, null, null, null, null,
        null, 0L);
  }
}
