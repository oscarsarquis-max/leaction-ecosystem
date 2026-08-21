package br.com.banco.spider.execution.idempotency;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.persistence.idempotency.IdempotencyReservationStatus;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyScope;
import br.com.banco.spider.execution.persistence.support.InMemoryPersistenceBundle;
import br.com.banco.spider.execution.route.CanonicalRouteFixtures;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class IdempotencyReservationTest {

  @Test
  void firstReserveIsNew() {
    var bundle =
        new InMemoryPersistenceBundle(
            SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")),
            IdentifierGenerator.sequential("i"));
    var req = CanonicalRouteFixtures.request("e1", "key-1");
    var scope =
        new IdempotencyScope("orig", "CAP", "OP", "1");
    var result = bundle.coordinator.reserveOrCreate(req, scope, "key-1", true);
    assertEquals(IdempotencyReservationStatus.RESERVED_NEW, result.status());
  }

  @Test
  void sameKeyFingerprintInProgressReturnsExisting() {
    var bundle =
        new InMemoryPersistenceBundle(
            SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")),
            IdentifierGenerator.sequential("i"));
    var scope = new IdempotencyScope("orig", "CAP", "OP", "1");
    bundle.coordinator.reserveOrCreate(CanonicalRouteFixtures.request("e1", "k"), scope, "k", true);
    var second =
        bundle.coordinator.reserveOrCreate(CanonicalRouteFixtures.request("e2", "k"), scope, "k", true);
    assertEquals(IdempotencyReservationStatus.IN_PROGRESS_SAME_REQUEST, second.status());
    assertEquals("e1", second.existingExecutionId());
  }

  @Test
  void divergentFingerprintConflicts() {
    var bundle =
        new InMemoryPersistenceBundle(
            SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")),
            IdentifierGenerator.sequential("i"));
    var scope = new IdempotencyScope("orig", "CAP", "OP", "1");
    bundle.coordinator.reserveOrCreate(
        CanonicalRouteFixtures.request("e1", "k", "SUCCESS"), scope, "k", true);
    var conflict =
        bundle.coordinator.reserveOrCreate(
            CanonicalRouteFixtures.request("e2", "k", "TECHNICAL_FAILURE"), scope, "k", true);
    assertEquals(IdempotencyReservationStatus.CONFLICTING_REQUEST, conflict.status());
  }

  @Test
  void concurrentReserveCreatesSingleLogicalExecution() throws Exception {
    var bundle =
        new InMemoryPersistenceBundle(
            SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")),
            IdentifierGenerator.sequential("i"));
    var scope = new IdempotencyScope("orig", "CAP", "OP", "1");
    CountDownLatch start = new CountDownLatch(1);
    AtomicInteger reservedNew = new AtomicInteger();
    try (var pool = Executors.newFixedThreadPool(8)) {
      List<Future<?>> futures = new ArrayList<>();
      for (int i = 0; i < 8; i++) {
        int idx = i;
        futures.add(
            pool.submit(
                () -> {
                  start.await();
                  var r =
                      bundle.coordinator.reserveOrCreate(
                          CanonicalRouteFixtures.request("e-c-" + idx, "race-key"),
                          scope,
                          "race-key",
                          true);
                  if (r.status() == IdempotencyReservationStatus.RESERVED_NEW) {
                    reservedNew.incrementAndGet();
                  }
                  return null;
                }));
      }
      start.countDown();
      for (Future<?> f : futures) {
        f.get(5, TimeUnit.SECONDS);
      }
    }
    assertEquals(1, reservedNew.get());
    assertTrue(
        bundle.idempotencyStore.findByScopeAndKeyHash(scope.scopeHash(), bundle.keyHash.hash("race-key"))
            .isPresent());
  }
}
