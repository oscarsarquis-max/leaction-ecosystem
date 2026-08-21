package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionWaitEntity;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ExecutionWaitJpaRepository extends JpaRepository<ExecutionWaitEntity, String> {

  @Query(
      """
      select w from ExecutionWaitEntity w
      where w.executionId = :executionId and w.stepId = :stepId
        and w.state in :states
      """)
  Optional<ExecutionWaitEntity> findActive(
      @Param("executionId") String executionId,
      @Param("stepId") String stepId,
      @Param("states") List<WaitState> states);

  Optional<ExecutionWaitEntity> findByExpectedSourceRefAndExternalOperationRefAndStateIn(
      String sourceRef, String externalOperationRef, List<WaitState> states);

  Optional<ExecutionWaitEntity> findByContinuationTokenFingerprint(String continuationTokenFingerprint);

  List<ExecutionWaitEntity> findByStateAndExpiresAtLessThanEqual(WaitState state, Instant now);

  List<ExecutionWaitEntity> findByStateIn(List<WaitState> states);

  List<ExecutionWaitEntity> findByExecutionId(String executionId);
}
