package br.com.banco.spider.operational.capacity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

/**
 * O bulkhead precisa ser exato sob concorrência: nunca conceder mais vagas do que a capacidade
 * declarada e nunca deixar ocupação pendurada depois das liberações.
 */
class BulkheadServiceTest {

  private static final String SCOPE = "schedule:sched:test@1";

  private final CapacityTestSupport.MutableClock clock =
      new CapacityTestSupport.MutableClock(CapacityTestSupport.T0);
  private final BulkheadService bulkheads = new BulkheadService(clock);

  @Test
  void acquiresUpToTheDeclaredCapacityAndRefusesTheNext() {
    assertTrue(bulkheads.tryAcquire(SCOPE, 2));
    assertTrue(bulkheads.tryAcquire(SCOPE, 2));
    assertFalse(bulkheads.tryAcquire(SCOPE, 2));

    assertEquals(2, bulkheads.occupied(SCOPE));
    assertTrue(bulkheads.saturated(SCOPE, 2));
  }

  @Test
  void scopeWithoutDeclaredCapacityDoesNotRequireReservation() {
    assertEquals(BulkheadAcquisition.NOT_REQUIRED, bulkheads.acquire("schedule:unknown@1"));
    assertEquals(BulkheadAcquisition.NOT_REQUIRED, bulkheads.acquire(null));
    assertTrue(bulkheads.tryAcquire(SCOPE, 0), "limite não positivo significa sem limite");
    assertEquals(0, bulkheads.occupied(SCOPE));
  }

  @Test
  void registeredScopeReservesAndReportsSaturation() {
    bulkheads.register(SCOPE, 1);

    assertEquals(BulkheadAcquisition.ACQUIRED, bulkheads.acquire(SCOPE));
    assertEquals(BulkheadAcquisition.SATURATED, bulkheads.acquire(SCOPE));

    bulkheads.release(SCOPE);
    assertEquals(BulkheadAcquisition.ACQUIRED, bulkheads.acquire(SCOPE));
  }

  @Test
  void releaseIsIdempotentAndNeverOpensPhantomCapacity() {
    bulkheads.register(SCOPE, 1);
    assertTrue(bulkheads.tryAcquire(SCOPE, 1));

    bulkheads.release(SCOPE);
    bulkheads.release(SCOPE);
    bulkheads.release(SCOPE);

    assertEquals(0, bulkheads.occupied(SCOPE));
    assertTrue(bulkheads.tryAcquire(SCOPE, 1));
    assertFalse(bulkheads.tryAcquire(SCOPE, 1), "liberação duplicada não pode criar vaga extra");
  }

  @Test
  void concurrentContendersNeverExceedTheCapacity() throws InterruptedException {
    int capacity = 4;
    int contenders = 64;
    bulkheads.register(SCOPE, capacity);
    AtomicInteger granted = new AtomicInteger();
    AtomicInteger peak = new AtomicInteger();
    AtomicInteger inFlight = new AtomicInteger();
    CountDownLatch start = new CountDownLatch(1);
    CountDownLatch done = new CountDownLatch(contenders);

    try (ExecutorService pool = Executors.newFixedThreadPool(16)) {
      for (int attempt = 0; attempt < contenders; attempt++) {
        pool.execute(
            () -> {
              try {
                start.await();
                if (bulkheads.tryAcquire(SCOPE, capacity)) {
                  granted.incrementAndGet();
                  peak.accumulateAndGet(inFlight.incrementAndGet(), Math::max);
                  inFlight.decrementAndGet();
                  bulkheads.release(SCOPE);
                }
              } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
              } finally {
                done.countDown();
              }
            });
      }
      start.countDown();
      assertTrue(done.await(20, TimeUnit.SECONDS), "os contendores devem terminar");
    }

    assertTrue(granted.get() > 0, "alguma reserva precisa ter sido concedida");
    assertTrue(peak.get() <= capacity, "ocupação simultânea excedeu a capacidade: " + peak.get());
    assertEquals(0, bulkheads.occupied(SCOPE), "toda reserva concedida deve ter sido devolvida");
  }

  @Test
  void statesExposeCapacityAndOccupancyPerScope() {
    bulkheads.register(SCOPE, 2);
    bulkheads.register("schedule:sched:other@1", 1);
    assertTrue(bulkheads.tryAcquire(SCOPE, 2));

    var states = bulkheads.states();

    assertEquals(2, states.size());
    BulkheadState observed =
        states.stream().filter(state -> state.scopeKey().equals(SCOPE)).findFirst().orElseThrow();
    assertEquals(2, observed.capacity());
    assertEquals(1, observed.occupied());
    assertEquals(CapacityTestSupport.T0, observed.updatedAt());
  }
}
