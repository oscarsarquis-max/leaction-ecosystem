package br.com.banco.spider.operational.workers;

import java.time.Duration;
import java.time.Instant;
import java.util.Objects;

/**
 * Agendamento durável de um tipo de worker. {@code version} é o controle otimista da linha e
 * {@code fencingToken} é monotônico por claim — um dono antigo nunca conclui um claim novo.
 */
public record DurableSchedule(
    String scheduleCode,
    long version,
    String scheduleVersion,
    WorkerType workerType,
    boolean enabled,
    Duration interval,
    Instant nextEligibleAt,
    Instant lastStartedAt,
    Instant lastCompletedAt,
    ScheduleOutcome lastOutcome,
    String ownerWorkerId,
    Instant leaseUntil,
    long fencingToken) {

  public DurableSchedule {
    Objects.requireNonNull(scheduleCode, "scheduleCode");
    Objects.requireNonNull(scheduleVersion, "scheduleVersion");
    Objects.requireNonNull(workerType, "workerType");
    Objects.requireNonNull(interval, "interval");
    Objects.requireNonNull(nextEligibleAt, "nextEligibleAt");
  }

  public static DurableSchedule seed(WorkerTypeDefinition definition, boolean enabled, Instant now) {
    return new DurableSchedule(
        definition.scheduleCode(),
        0L,
        definition.scheduleVersion(),
        definition.workerType(),
        enabled,
        definition.interval(),
        now,
        null,
        null,
        null,
        null,
        null,
        0L);
  }

  public boolean leaseHeldAt(Instant now) {
    return ownerWorkerId != null && leaseUntil != null && leaseUntil.isAfter(now);
  }

  public boolean leaseExpiredAt(Instant now) {
    return ownerWorkerId != null && (leaseUntil == null || !leaseUntil.isAfter(now));
  }

  public boolean eligibleAt(Instant now) {
    return enabled && !nextEligibleAt.isAfter(now);
  }

  public DurableSchedule withEnabled(boolean value) {
    return new DurableSchedule(
        scheduleCode,
        version + 1,
        scheduleVersion,
        workerType,
        value,
        interval,
        nextEligibleAt,
        lastStartedAt,
        lastCompletedAt,
        lastOutcome,
        ownerWorkerId,
        leaseUntil,
        fencingToken);
  }
}
