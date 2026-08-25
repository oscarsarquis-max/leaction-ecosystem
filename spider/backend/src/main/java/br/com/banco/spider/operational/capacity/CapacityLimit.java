package br.com.banco.spider.operational.capacity;

import java.time.Duration;

/**
 * Limites declarados de um escopo.
 *
 * <p>Convenção de "sem limite": {@code maxConcurrency <= 0} e {@code quotaPerWindow <= 0} desligam a
 * respectiva proteção; para os limites de backlog o valor negativo é que desliga, porque zero é um
 * limite legítimo (qualquer trabalho pendente já é excesso).
 */
public record CapacityLimit(
    int maxConcurrency,
    int softBacklogLimit,
    int hardBacklogLimit,
    int quotaPerWindow,
    Duration window,
    Duration acquireTimeout) {

  public static final int NO_LIMIT = -1;

  public CapacityLimit {
    window = window == null ? Duration.ofMinutes(1) : window;
    acquireTimeout = acquireTimeout == null ? Duration.ZERO : acquireTimeout;
    if (window.isZero() || window.isNegative()) {
      throw new IllegalArgumentException("window must be positive");
    }
    if (acquireTimeout.isNegative()) {
      throw new IllegalArgumentException("acquireTimeout must not be negative");
    }
    if (hardBacklogLimit >= 0 && softBacklogLimit > hardBacklogLimit) {
      throw new IllegalArgumentException("softBacklogLimit must not exceed hardBacklogLimit");
    }
  }

  public static CapacityLimit unlimited() {
    return new CapacityLimit(0, NO_LIMIT, NO_LIMIT, 0, Duration.ofMinutes(1), Duration.ZERO);
  }

  public boolean limitsConcurrency() {
    return maxConcurrency > 0;
  }

  public boolean limitsQuota() {
    return quotaPerWindow > 0;
  }

  public boolean limitsSoftBacklog() {
    return softBacklogLimit >= 0;
  }

  public boolean limitsHardBacklog() {
    return hardBacklogLimit >= 0;
  }
}
