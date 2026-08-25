package br.com.banco.spider.operational.health;

import java.time.Duration;

public class ProvisionalSloEvaluator {

  public SloEvaluation evaluate(SliResult result, ProvisionalSloObjective objective) {
    if (result.status() == SliStatus.INSUFFICIENT_DATA) {
      return new SloEvaluation(
          1, objective.code(), result.code(), SloComplianceStatus.INSUFFICIENT_DATA,
          result.value(), targetValue(objective), "Amostra abaixo do mínimo provisório");
    }
    if (result.status() != SliStatus.AVAILABLE || result.value() == null) {
      return new SloEvaluation(
          1, objective.code(), result.code(), SloComplianceStatus.UNKNOWN,
          result.value(), targetValue(objective), "SLI indisponível");
    }
    double target = targetValue(objective);
    double value = result.value();
    double factor = objective.atRiskFactor() > 0 ? objective.atRiskFactor() : 0.9;
    SloComplianceStatus status;
    if (objective.higherIsBetter()) {
      status =
          value >= target
              ? SloComplianceStatus.MET
              : value >= target * factor
                  ? SloComplianceStatus.AT_RISK
                  : SloComplianceStatus.MISSED;
    } else {
      status =
          value <= target
              ? SloComplianceStatus.MET
              : value <= target / factor
                  ? SloComplianceStatus.AT_RISK
                  : SloComplianceStatus.MISSED;
    }
    return new SloEvaluation(
        1, objective.code(), result.code(), status, value, target, "Objetivo provisório MOCK_ONLY");
  }

  public ErrorBudgetEvaluation evaluateErrorBudget(
      SliResult result, ProvisionalSloObjective objective) {
    if (!objective.higherIsBetter() || objective.target() == null) {
      return new ErrorBudgetEvaluation(
          1, objective.code(), ErrorBudgetStatus.NOT_APPLICABLE, null, null, null,
          "Error budget aplica-se somente a razões de confiabilidade");
    }
    if (result.status() == SliStatus.INSUFFICIENT_DATA) {
      return new ErrorBudgetEvaluation(
          1, objective.code(), ErrorBudgetStatus.INSUFFICIENT_DATA, null, null, null,
          "Amostra insuficiente");
    }
    if (result.value() == null || result.status() != SliStatus.AVAILABLE) {
      return new ErrorBudgetEvaluation(
          1, objective.code(), ErrorBudgetStatus.UNKNOWN, null, null, null, "SLI indisponível");
    }
    double allowed = Math.max(0, 1 - objective.target());
    double observed = Math.max(0, 1 - result.value());
    double consumed;
    ErrorBudgetStatus status;
    if (allowed == 0) {
      consumed = observed == 0 ? 0 : Double.POSITIVE_INFINITY;
      status = observed == 0 ? ErrorBudgetStatus.AVAILABLE : ErrorBudgetStatus.EXHAUSTED;
    } else {
      consumed = observed / allowed;
      status =
          consumed <= 0.8
              ? ErrorBudgetStatus.AVAILABLE
              : consumed <= 1 ? ErrorBudgetStatus.AT_RISK : ErrorBudgetStatus.EXHAUSTED;
    }
    return new ErrorBudgetEvaluation(
        1, objective.code(), status, allowed, observed, consumed, "Consumo provisório");
  }

  private static double targetValue(ProvisionalSloObjective objective) {
    if (objective.target() != null) {
      return objective.target();
    }
    if (objective.threshold() == null) {
      throw new IllegalArgumentException("Objective must define target or threshold");
    }
    return Duration.parse(objective.threshold()).toMillis();
  }
}
