package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionPlanStore implements ExecutionPlanStorePort {

  private final Map<String, PersistedExecutionPlan> byPlanId = new ConcurrentHashMap<>();
  private final Map<String, String> executionToPlan = new ConcurrentHashMap<>();

  @Override
  public void insert(PersistedExecutionPlan plan) {
    if (byPlanId.putIfAbsent(plan.planId(), plan) != null) {
      throw new IllegalStateException("Plan already exists: " + plan.planId());
    }
    if (executionToPlan.putIfAbsent(plan.executionId(), plan.planId()) != null) {
      byPlanId.remove(plan.planId());
      throw new IllegalStateException("Plan already exists for execution: " + plan.executionId());
    }
  }

  @Override
  public Optional<PersistedExecutionPlan> findByPlanId(String planId) {
    return Optional.ofNullable(byPlanId.get(planId));
  }

  @Override
  public Optional<PersistedExecutionPlan> findByExecutionId(String executionId) {
    String planId = executionToPlan.get(executionId);
    return planId == null ? Optional.empty() : findByPlanId(planId);
  }

  public void clear() {
    byPlanId.clear();
    executionToPlan.clear();
  }
}
