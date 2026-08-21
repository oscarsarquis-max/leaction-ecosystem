package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import java.util.Optional;

public interface ExecutionPlanStorePort {
  void insert(PersistedExecutionPlan plan);

  Optional<PersistedExecutionPlan> findByPlanId(String planId);

  Optional<PersistedExecutionPlan> findByExecutionId(String executionId);
}
