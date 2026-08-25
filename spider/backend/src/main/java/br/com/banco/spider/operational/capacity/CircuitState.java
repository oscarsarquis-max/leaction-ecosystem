package br.com.banco.spider.operational.capacity;

import java.time.Instant;

/** Estado observável de um disjuntor de capacidade. */
public record CircuitState(
    String scopeKey,
    CircuitPhase phase,
    int failureCount,
    int successCount,
    Instant openedAt,
    Instant probeAfter,
    int probeInFlight,
    Instant updatedAt) {

  public static CircuitState closed(String scopeKey, Instant now) {
    return new CircuitState(scopeKey, CircuitPhase.CLOSED, 0, 0, null, null, 0, now);
  }
}
