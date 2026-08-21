package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import java.util.List;
import java.util.Optional;

public interface ExecutionRecoveryQueryPort {
  Optional<ExecutionControlRecord> findByExecutionId(String executionId);

  List<ExecutionControlRecord> findRecoverableExecutions();

  Optional<PersistedExecutionPlan> findPlanByExecutionId(String executionId);
}
