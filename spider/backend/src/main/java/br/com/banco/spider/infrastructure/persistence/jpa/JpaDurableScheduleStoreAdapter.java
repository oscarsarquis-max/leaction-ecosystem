package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.RuntimeScheduleEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.RuntimeScheduleJpaRepository;
import br.com.banco.spider.operational.workers.DurableSchedule;
import br.com.banco.spider.operational.workers.DurableScheduleStorePort;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import java.time.Duration;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import org.springframework.transaction.annotation.Transactional;

/**
 * Mesma semântica de CAS do adaptador em memória, porém a condição de claim inteira vive no WHERE
 * da instrução de atualização — a exclusão mútua é do banco, não do processo.
 */
public class JpaDurableScheduleStoreAdapter implements DurableScheduleStorePort {

  private final RuntimeScheduleJpaRepository repo;

  public JpaDurableScheduleStoreAdapter(RuntimeScheduleJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public DurableSchedule upsert(DurableSchedule schedule) {
    return toModel(repo.save(toEntity(schedule)));
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<DurableSchedule> findByCode(String scheduleCode) {
    return scheduleCode == null ? Optional.empty() : repo.findById(scheduleCode).map(this::toModel);
  }

  @Override
  @Transactional(readOnly = true)
  public List<DurableSchedule> findAll() {
    return repo.findAll().stream()
        .sorted(Comparator.comparing(RuntimeScheduleEntity::getScheduleCode))
        .map(this::toModel)
        .toList();
  }

  @Override
  @Transactional(readOnly = true)
  public List<DurableSchedule> findEligible(Instant now, int limit) {
    return repo.findEligible(now).stream()
        .limit(Math.max(0, limit))
        .map(this::toModel)
        .toList();
  }

  @Override
  @Transactional
  public Optional<DurableSchedule> tryClaim(
      String scheduleCode, long expectedVersion, String workerId, Instant now, Instant leaseUntil) {
    if (scheduleCode == null || workerId == null) {
      return Optional.empty();
    }
    int claimed = repo.claim(scheduleCode, expectedVersion, workerId, now, leaseUntil);
    if (claimed == 0) {
      return Optional.empty();
    }
    return repo.findById(scheduleCode).map(this::toModel);
  }

  @Override
  @Transactional
  public boolean complete(
      String scheduleCode,
      String workerId,
      long fencingToken,
      Instant now,
      ScheduleOutcome outcome,
      Instant nextEligibleAt) {
    if (scheduleCode == null || workerId == null) {
      return false;
    }
    Instant next =
        nextEligibleAt != null
            ? nextEligibleAt
            : repo.findById(scheduleCode).map(RuntimeScheduleEntity::getNextEligibleAt).orElse(now);
    return repo.complete(scheduleCode, workerId, fencingToken, now, outcome, next) > 0;
  }

  @Override
  @Transactional(readOnly = true)
  public boolean isCurrentOwner(String scheduleCode, String workerId, long fencingToken) {
    if (scheduleCode == null || workerId == null) {
      return false;
    }
    return repo.findById(scheduleCode)
        .map(e -> workerId.equals(e.getOwnerWorkerId()) && e.getFencingToken() == fencingToken)
        .orElse(false);
  }

  @Override
  @Transactional
  public void seed(List<DurableSchedule> schedules) {
    if (schedules == null) {
      return;
    }
    for (DurableSchedule schedule : schedules) {
      if (!repo.existsById(schedule.scheduleCode())) {
        repo.save(toEntity(schedule));
      }
    }
  }

  @Override
  @Transactional
  public Optional<DurableSchedule> simulateLeaseExpiry(
      String scheduleCode, Instant expiredLeaseUntil) {
    if (scheduleCode == null || repo.expireLease(scheduleCode, expiredLeaseUntil) == 0) {
      return Optional.empty();
    }
    return repo.findById(scheduleCode).map(this::toModel);
  }

  private RuntimeScheduleEntity toEntity(DurableSchedule schedule) {
    RuntimeScheduleEntity e = new RuntimeScheduleEntity();
    e.setScheduleCode(schedule.scheduleCode());
    e.setScheduleDefVersion(schedule.scheduleVersion());
    e.setWorkerType(schedule.workerType());
    e.setEnabled(schedule.enabled());
    e.setIntervalSeconds(Math.max(1L, schedule.interval().toSeconds()));
    e.setNextEligibleAt(schedule.nextEligibleAt());
    e.setLastStartedAt(schedule.lastStartedAt());
    e.setLastCompletedAt(schedule.lastCompletedAt());
    e.setLastOutcome(schedule.lastOutcome());
    e.setOwnerWorkerId(schedule.ownerWorkerId());
    e.setLeaseUntil(schedule.leaseUntil());
    e.setFencingToken(schedule.fencingToken());
    e.setVersion(schedule.version());
    return e;
  }

  private DurableSchedule toModel(RuntimeScheduleEntity e) {
    return new DurableSchedule(
        e.getScheduleCode(),
        e.getVersion(),
        e.getScheduleDefVersion(),
        e.getWorkerType(),
        e.isEnabled(),
        Duration.ofSeconds(e.getIntervalSeconds()),
        e.getNextEligibleAt(),
        e.getLastStartedAt(),
        e.getLastCompletedAt(),
        e.getLastOutcome(),
        e.getOwnerWorkerId(),
        e.getLeaseUntil(),
        e.getFencingToken());
  }
}
