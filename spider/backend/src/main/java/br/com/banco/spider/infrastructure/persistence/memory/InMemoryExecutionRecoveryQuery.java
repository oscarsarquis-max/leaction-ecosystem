package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionRecoveryQueryPort;
import java.util.EnumSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;

public class InMemoryExecutionRecoveryQuery implements ExecutionRecoveryQueryPort {

  private static final Set<ExecutionState> RECOVERABLE =
      EnumSet.of(
          ExecutionState.RECEIVED,
          ExecutionState.VALIDATED,
          ExecutionState.RESOLVED,
          ExecutionState.PLANNED,
          ExecutionState.RUNNING,
          ExecutionState.WAITING_EXTERNAL,
          ExecutionState.COMPENSATING);

  private final ExecutionControlStorePort controlStore;
  private final ExecutionPlanStorePort planStore;

  public InMemoryExecutionRecoveryQuery(
      ExecutionControlStorePort controlStore, ExecutionPlanStorePort planStore) {
    this.controlStore = controlStore;
    this.planStore = planStore;
  }

  @Override
  public Optional<ExecutionControlRecord> findByExecutionId(String executionId) {
    return controlStore.findByExecutionId(executionId);
  }

  @Override
  public List<ExecutionControlRecord> findRecoverableExecutions() {
    return controlStore.findByStates(List.copyOf(RECOVERABLE));
  }

  @Override
  public Optional<PersistedExecutionPlan> findPlanByExecutionId(String executionId) {
    return planStore.findByExecutionId(executionId);
  }
}
