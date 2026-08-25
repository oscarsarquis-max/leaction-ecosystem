package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Bulkheads em memória, um por escopo. A reserva é sempre não bloqueante: o chamador que não
 * consegue lugar desiste do ciclo em vez de acumular espera dentro do runtime.
 *
 * <p>A liberação é idempotente e nunca deixa a ocupação negativa — o runner libera em {@code
 * finally}, e um {@code release} duplicado não pode abrir espaço fantasma.
 */
public class BulkheadService {

  private final SpiderClock clock;
  private final Map<String, AtomicInteger> occupied = new ConcurrentHashMap<>();
  private final Map<String, Integer> capacities = new ConcurrentHashMap<>();

  public BulkheadService(SpiderClock clock) {
    this.clock = clock;
  }

  /** Declara a capacidade do escopo — chamado pela admissão a cada avaliação. */
  public void register(String scopeKey, int capacity) {
    if (scopeKey == null) {
      return;
    }
    if (capacity <= 0) {
      capacities.remove(scopeKey);
      return;
    }
    capacities.put(scopeKey, capacity);
    occupied.computeIfAbsent(scopeKey, key -> new AtomicInteger());
  }

  public boolean tryAcquire(String scopeKey, int limit) {
    if (scopeKey == null || limit <= 0) {
      return true;
    }
    register(scopeKey, limit);
    AtomicInteger counter = occupied.computeIfAbsent(scopeKey, key -> new AtomicInteger());
    while (true) {
      int current = counter.get();
      if (current >= limit) {
        return false;
      }
      if (counter.compareAndSet(current, current + 1)) {
        return true;
      }
    }
  }

  /** Reserva usando a capacidade declarada para o escopo. */
  public BulkheadAcquisition acquire(String scopeKey) {
    if (scopeKey == null) {
      return BulkheadAcquisition.NOT_REQUIRED;
    }
    Integer limit = capacities.get(scopeKey);
    if (limit == null || limit <= 0) {
      return BulkheadAcquisition.NOT_REQUIRED;
    }
    return tryAcquire(scopeKey, limit)
        ? BulkheadAcquisition.ACQUIRED
        : BulkheadAcquisition.SATURATED;
  }

  public void release(String scopeKey) {
    if (scopeKey == null) {
      return;
    }
    AtomicInteger counter = occupied.get(scopeKey);
    if (counter == null) {
      return;
    }
    counter.updateAndGet(current -> Math.max(0, current - 1));
  }

  public int occupied(String scopeKey) {
    AtomicInteger counter = scopeKey == null ? null : occupied.get(scopeKey);
    return counter == null ? 0 : counter.get();
  }

  public int capacity(String scopeKey) {
    Integer limit = scopeKey == null ? null : capacities.get(scopeKey);
    return limit == null ? 0 : limit;
  }

  public boolean saturated(String scopeKey, int limit) {
    return limit > 0 && occupied(scopeKey) >= limit;
  }

  public List<BulkheadState> states() {
    Instant now = clock.now();
    List<BulkheadState> states = new ArrayList<>();
    for (Map.Entry<String, AtomicInteger> entry : occupied.entrySet()) {
      states.add(
          new BulkheadState(
              entry.getKey(), capacity(entry.getKey()), entry.getValue().get(), 0, now));
    }
    states.sort(Comparator.comparing(BulkheadState::scopeKey));
    return List.copyOf(states);
  }
}
