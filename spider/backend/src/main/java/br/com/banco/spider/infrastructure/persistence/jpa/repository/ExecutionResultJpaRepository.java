package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionResultEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExecutionResultJpaRepository extends JpaRepository<ExecutionResultEntity, String> {
  Optional<ExecutionResultEntity> findByExecutionId(String executionId);
}
