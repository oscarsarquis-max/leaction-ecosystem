package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionGovernanceFixationEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExecutionGovernanceFixationJpaRepository
    extends JpaRepository<ExecutionGovernanceFixationEntity, String> {

  Optional<ExecutionGovernanceFixationEntity> findByExecutionId(String executionId);
}
