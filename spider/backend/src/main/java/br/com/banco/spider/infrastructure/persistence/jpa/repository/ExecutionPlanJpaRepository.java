package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionPlanEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExecutionPlanJpaRepository extends JpaRepository<ExecutionPlanEntity, String> {
  Optional<ExecutionPlanEntity> findByExecutionId(String executionId);
}
