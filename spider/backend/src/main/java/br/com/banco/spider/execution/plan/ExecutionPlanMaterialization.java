package br.com.banco.spider.execution.plan;

import br.com.banco.spider.canonical.error.CanonicalError;
import java.util.List;

public record ExecutionPlanMaterialization(
    boolean success, ExecutionPlan plan, List<CanonicalError> errors) {

  public ExecutionPlanMaterialization {
    errors = errors == null ? List.of() : List.copyOf(errors);
  }

  public static ExecutionPlanMaterialization ok(ExecutionPlan plan) {
    return new ExecutionPlanMaterialization(true, plan, List.of());
  }

  public static ExecutionPlanMaterialization failed(List<CanonicalError> errors) {
    return new ExecutionPlanMaterialization(false, null, errors);
  }
}
