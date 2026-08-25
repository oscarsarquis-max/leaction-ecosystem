package br.com.banco.spider.operational.workers;

import java.time.Duration;
import java.util.Objects;

/** Definição imutável de um tipo de worker. Sempre vem do catálogo fechado, nunca da borda. */
public record WorkerTypeDefinition(
    WorkerType workerType,
    String scheduleCode,
    String scheduleVersion,
    Duration interval,
    int batchSize,
    Duration leaseDuration,
    Duration executionTimeout,
    int maxAttempts,
    int concurrencyLimit) {

  public WorkerTypeDefinition {
    Objects.requireNonNull(workerType, "workerType");
    Objects.requireNonNull(scheduleCode, "scheduleCode");
    Objects.requireNonNull(scheduleVersion, "scheduleVersion");
    Objects.requireNonNull(interval, "interval");
    Objects.requireNonNull(leaseDuration, "leaseDuration");
    Objects.requireNonNull(executionTimeout, "executionTimeout");
    if (interval.isZero() || interval.isNegative()) {
      throw new IllegalArgumentException("interval must be positive: " + scheduleCode);
    }
    if (batchSize < 1) {
      throw new IllegalArgumentException("batchSize must be >= 1: " + scheduleCode);
    }
    if (maxAttempts < 1) {
      throw new IllegalArgumentException("maxAttempts must be >= 1: " + scheduleCode);
    }
    if (concurrencyLimit < 1) {
      throw new IllegalArgumentException("concurrencyLimit must be >= 1: " + scheduleCode);
    }
  }
}
