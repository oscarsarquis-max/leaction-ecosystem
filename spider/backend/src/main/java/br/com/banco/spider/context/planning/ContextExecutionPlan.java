package br.com.banco.spider.context.planning;

import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentProvenance;
import java.util.List;

/**
 * Plano empresarial determinado antes de routes/adapters.
 *
 * <p>É distinto do plano técnico imutável materializado pelo Data Plane para uma execução.
 */
public record ContextExecutionPlan(
    String schemaVersion,
    String planId,
    String planType,
    String intent,
    List<ContextExecutionPlanStep> steps,
    IntentConstraints constraints,
    IntentProvenance provenance,
    ContextExecutionPlanStatus status,
    List<String> statusReasons) {

  public ContextExecutionPlan {
    steps = steps == null ? List.of() : List.copyOf(steps);
    statusReasons = statusReasons == null ? List.of() : List.copyOf(statusReasons);
  }
}
