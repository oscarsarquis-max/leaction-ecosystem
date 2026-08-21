package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.callback.CallbackReconciliationState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.CallbackReconciliationEntity;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface CallbackReconciliationJpaRepository
    extends JpaRepository<CallbackReconciliationEntity, String> {

  Optional<CallbackReconciliationEntity> findByOutboxId(String outboxId);

  Optional<CallbackReconciliationEntity> findByExecutionId(String executionId);

  @Query(
      """
      select e from CallbackReconciliationEntity e
      where e.state in :states
        and e.nextQueryAt <= :now
        and e.expiresAt > :now
        and (e.leaseUntil is null or e.leaseUntil < :now)
      order by e.nextQueryAt asc, e.reconciliationId asc
      """)
  List<CallbackReconciliationEntity> findDue(
      @Param("states") List<CallbackReconciliationState> states, @Param("now") Instant now);

  List<CallbackReconciliationEntity> findByStateAndLeaseUntilLessThanEqual(
      CallbackReconciliationState state, Instant leaseUntil);
}
