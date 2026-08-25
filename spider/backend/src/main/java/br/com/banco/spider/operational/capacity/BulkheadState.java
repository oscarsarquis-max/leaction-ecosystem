package br.com.banco.spider.operational.capacity;

import java.time.Instant;

/** Estado observável de um bulkhead. Somente contagens; nada de identidade de trabalho. */
public record BulkheadState(
    String scopeKey, int capacity, int occupied, int waiting, Instant updatedAt) {

  public boolean saturated() {
    return capacity > 0 && occupied >= capacity;
  }

  public int utilizationPercent() {
    return capacity <= 0 ? 0 : Math.min(100, occupied * 100 / capacity);
  }
}
