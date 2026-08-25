package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.RuntimeWorkerInstanceEntity;
import br.com.banco.spider.operational.workers.WorkerInstanceStatus;
import java.time.Instant;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Modifying;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface RuntimeWorkerInstanceJpaRepository
    extends JpaRepository<RuntimeWorkerInstanceEntity, String> {

  @Query(
      """
      select e from RuntimeWorkerInstanceEntity e
      where e.status in :activeStatuses
        and (e.lastHeartbeatAt is null or e.lastHeartbeatAt < :staleBefore)
      order by e.workerId asc
      """)
  List<RuntimeWorkerInstanceEntity> findStale(
      @Param("activeStatuses") List<WorkerInstanceStatus> activeStatuses,
      @Param("staleBefore") Instant staleBefore);

  /** Transição condicional pelo estado observado — sem leitura-e-escrita fora de transação. */
  @Modifying(clearAutomatically = true, flushAutomatically = true)
  @Query(
      """
      update RuntimeWorkerInstanceEntity e
      set e.status = :newStatus,
          e.lastHeartbeatAt = :now,
          e.stoppedAt = :stoppedAt,
          e.version = e.version + 1
      where e.workerId = :workerId
        and e.status = :expectedStatus
      """)
  int compareAndSetStatus(
      @Param("workerId") String workerId,
      @Param("expectedStatus") WorkerInstanceStatus expectedStatus,
      @Param("newStatus") WorkerInstanceStatus newStatus,
      @Param("stoppedAt") Instant stoppedAt,
      @Param("now") Instant now);
}
