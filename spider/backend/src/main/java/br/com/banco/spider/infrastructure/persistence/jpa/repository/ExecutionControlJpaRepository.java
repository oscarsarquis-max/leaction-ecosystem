package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionControlEntity;
import java.util.Collection;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ExecutionControlJpaRepository extends JpaRepository<ExecutionControlEntity, String> {
  List<ExecutionControlEntity> findByStateIn(Collection<ExecutionState> states);
}
