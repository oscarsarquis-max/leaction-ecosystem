package br.com.banco.spider.operational.health;

import java.time.Instant;
import java.util.List;

public record OperationalHealthSnapshot(
    int schemaVersion,
    Instant generatedAt,
    String integrationLevel,
    boolean provisional,
    HealthStatus overallStatus,
    OperationalHealthWindow window,
    List<SliResult> slis,
    List<SloEvaluation> sloEvaluations,
    List<ErrorBudgetEvaluation> errorBudgets,
    List<HealthDimensionStatus> dimensions,
    DataQualitySummary dataQuality) {
  public OperationalHealthSnapshot {
    slis = List.copyOf(slis);
    sloEvaluations = List.copyOf(sloEvaluations);
    errorBudgets = List.copyOf(errorBudgets);
    dimensions = List.copyOf(dimensions);
  }
}
