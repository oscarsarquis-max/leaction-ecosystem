package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.operational.workers.DurableSchedule;
import br.com.banco.spider.operational.workers.DurableScheduleStorePort;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Agendamentos duráveis em memória. Todo caminho de mutação é {@code synchronized} para que o CAS
 * de claim e a conclusão com fencing tenham a mesma semântica do adaptador JPA.
 */
public class InMemoryDurableScheduleStore implements DurableScheduleStorePort {

  private final Map<String, DurableSchedule> byCode = new ConcurrentHashMap<>();

  @Override
  public synchronized DurableSchedule upsert(DurableSchedule schedule) {
    byCode.put(schedule.scheduleCode(), schedule);
    return schedule;
  }

  @Override
  public Optional<DurableSchedule> findByCode(String scheduleCode) {
    return scheduleCode == null ? Optional.empty() : Optional.ofNullable(byCode.get(scheduleCode));
  }

  @Override
  public List<DurableSchedule> findAll() {
    return byCode.values().stream()
        .sorted(Comparator.comparing(DurableSchedule::scheduleCode))
        .toList();
  }

  @Override
  public List<DurableSchedule> findEligible(Instant now, int limit) {
    return byCode.values().stream()
        .filter(schedule -> schedule.eligibleAt(now))
        .filter(schedule -> !schedule.leaseHeldAt(now))
        .sorted(
            Comparator.comparing(DurableSchedule::nextEligibleAt)
                .thenComparing(DurableSchedule::scheduleCode))
        .limit(Math.max(0, limit))
        .toList();
  }

  @Override
  public synchronized Optional<DurableSchedule> tryClaim(
      String scheduleCode, long expectedVersion, String workerId, Instant now, Instant leaseUntil) {
    DurableSchedule current = byCode.get(scheduleCode);
    if (current == null || workerId == null) {
      return Optional.empty();
    }
    if (current.version() != expectedVersion) {
      return Optional.empty();
    }
    if (!current.eligibleAt(now)) {
      return Optional.empty();
    }
    boolean ownershipFree =
        current.ownerWorkerId() == null
            || workerId.equals(current.ownerWorkerId())
            || current.leaseUntil() == null
            || current.leaseUntil().isBefore(now);
    if (!ownershipFree) {
      return Optional.empty();
    }
    DurableSchedule claimed =
        new DurableSchedule(
            current.scheduleCode(),
            current.version() + 1,
            current.scheduleVersion(),
            current.workerType(),
            current.enabled(),
            current.interval(),
            current.nextEligibleAt(),
            now,
            current.lastCompletedAt(),
            current.lastOutcome(),
            workerId,
            leaseUntil,
            current.fencingToken() + 1);
    byCode.put(scheduleCode, claimed);
    return Optional.of(claimed);
  }

  @Override
  public synchronized boolean complete(
      String scheduleCode,
      String workerId,
      long fencingToken,
      Instant now,
      ScheduleOutcome outcome,
      Instant nextEligibleAt) {
    DurableSchedule current = byCode.get(scheduleCode);
    if (current == null || workerId == null) {
      return false;
    }
    if (!workerId.equals(current.ownerWorkerId()) || current.fencingToken() != fencingToken) {
      return false;
    }
    DurableSchedule completed =
        new DurableSchedule(
            current.scheduleCode(),
            current.version() + 1,
            current.scheduleVersion(),
            current.workerType(),
            current.enabled(),
            current.interval(),
            nextEligibleAt == null ? current.nextEligibleAt() : nextEligibleAt,
            current.lastStartedAt(),
            now,
            outcome,
            null,
            null,
            current.fencingToken());
    byCode.put(scheduleCode, completed);
    return true;
  }

  @Override
  public boolean isCurrentOwner(String scheduleCode, String workerId, long fencingToken) {
    DurableSchedule current = byCode.get(scheduleCode);
    return current != null
        && workerId != null
        && workerId.equals(current.ownerWorkerId())
        && current.fencingToken() == fencingToken;
  }

  @Override
  public synchronized void seed(List<DurableSchedule> schedules) {
    if (schedules == null) {
      return;
    }
    for (DurableSchedule schedule : schedules) {
      byCode.putIfAbsent(schedule.scheduleCode(), schedule);
    }
  }

  @Override
  public synchronized Optional<DurableSchedule> simulateLeaseExpiry(
      String scheduleCode, Instant expiredLeaseUntil) {
    DurableSchedule current = byCode.get(scheduleCode);
    if (current == null || current.ownerWorkerId() == null) {
      return Optional.empty();
    }
    DurableSchedule expired =
        new DurableSchedule(
            current.scheduleCode(),
            current.version() + 1,
            current.scheduleVersion(),
            current.workerType(),
            current.enabled(),
            current.interval(),
            current.nextEligibleAt(),
            current.lastStartedAt(),
            current.lastCompletedAt(),
            current.lastOutcome(),
            current.ownerWorkerId(),
            expiredLeaseUntil,
            current.fencingToken());
    byCode.put(scheduleCode, expired);
    return Optional.of(expired);
  }
}
