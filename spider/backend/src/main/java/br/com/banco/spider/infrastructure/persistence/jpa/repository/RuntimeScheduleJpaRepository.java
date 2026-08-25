package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.RuntimeScheduleEntity;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import java.time.Instant;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RuntimeScheduleJpaRepository extends JpaRepository<RuntimeScheduleEntity, String> {

  @Query(
      """
      select e from RuntimeScheduleEntity e
      where e.enabled = true
        and e.nextEligibleAt <= :now
        and (e.ownerWorkerId is null or e.leaseUntil is null or e.leaseUntil < :now)
      order by e.nextEligibleAt asc, e.scheduleCode asc
      """)
  List<RuntimeScheduleEntity> findEligible(@Param("now") Instant now);

  /** CAS de claim: a condição inteira vive no WHERE, então dois workers nunca vencem juntos. */
  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query(
      """
      update RuntimeScheduleEntity e
      set e.ownerWorkerId = :workerId,
          e.leaseUntil = :leaseUntil,
          e.lastStartedAt = :now,
          e.fencingToken = e.fencingToken + 1,
          e.version = e.version + 1
      where e.scheduleCode = :scheduleCode
        and e.version = :expectedVersion
        and e.enabled = true
        and e.nextEligibleAt <= :now
        and (e.ownerWorkerId is null
             or e.ownerWorkerId = :workerId
             or e.leaseUntil is null
             or e.leaseUntil < :now)
      """)
  int claim(
      @Param("scheduleCode") String scheduleCode,
      @Param("expectedVersion") long expectedVersion,
      @Param("workerId") String workerId,
      @Param("now") Instant now,
      @Param("leaseUntil") Instant leaseUntil);

  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query(
      """
      update RuntimeScheduleEntity e
      set e.ownerWorkerId = null,
          e.leaseUntil = null,
          e.lastCompletedAt = :now,
          e.lastOutcome = :outcome,
          e.nextEligibleAt = :nextEligibleAt,
          e.version = e.version + 1
      where e.scheduleCode = :scheduleCode
        and e.ownerWorkerId = :workerId
        and e.fencingToken = :fencingToken
      """)
  int complete(
      @Param("scheduleCode") String scheduleCode,
      @Param("workerId") String workerId,
      @Param("fencingToken") long fencingToken,
      @Param("now") Instant now,
      @Param("outcome") ScheduleOutcome outcome,
      @Param("nextEligibleAt") Instant nextEligibleAt);

  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query(
      """
      update RuntimeScheduleEntity e
      set e.leaseUntil = :expiredLeaseUntil,
          e.version = e.version + 1
      where e.scheduleCode = :scheduleCode
        and e.ownerWorkerId is not null
      """)
  int expireLease(
      @Param("scheduleCode") String scheduleCode,
      @Param("expiredLeaseUntil") Instant expiredLeaseUntil);
}
