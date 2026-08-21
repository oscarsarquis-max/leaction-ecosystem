package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionTransitionEntity;
import java.util.List;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ExecutionTransitionJpaRepository
    extends JpaRepository<ExecutionTransitionEntity, String> {
  List<ExecutionTransitionEntity> findByExecutionIdOrderBySequenceNoAsc(String executionId);

  @Query("select coalesce(max(t.sequenceNo), 0) from ExecutionTransitionEntity t where t.executionId = :executionId")
  long maxSequence(@Param("executionId") String executionId);

  Optional<ExecutionTransitionEntity> findByExecutionIdAndSequenceNo(String executionId, long sequenceNo);
}
