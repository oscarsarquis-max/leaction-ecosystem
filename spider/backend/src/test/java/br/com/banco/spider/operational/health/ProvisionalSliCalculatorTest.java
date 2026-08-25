package br.com.banco.spider.operational.health;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class ProvisionalSliCalculatorTest {
  private static final Instant NOW = Instant.parse("2026-08-25T12:00:00Z");
  private final ProvisionalSliCalculator calculator =
      new ProvisionalSliCalculator(SpiderClock.fixed(NOW));

  @Test
  void calculatesTechnicalReliabilityAndIgnoresBusinessOutcome() {
    List<ExecutionControlRecord> executions =
        List.of(
            execution("ok", ExecutionState.SUCCEEDED, TechnicalStatus.SUCCESS, 100),
            execution("failed", ExecutionState.FAILED, TechnicalStatus.FAILURE, 200));
    SliResult result =
        calculate(
            definition(
                ProvisionalSliCalculator.EXECUTION_TECHNICAL_RELIABILITY,
                HealthDimensionCode.EXECUTION_FLOW,
                "ratio",
                true),
            executions);

    assertEquals(SliStatus.AVAILABLE, result.status());
    assertEquals(0.5, result.value());
    assertEquals(2, result.sampleSize());
  }

  @Test
  void calculatesNearestRankLatencyQuantiles() {
    List<ExecutionControlRecord> executions =
        List.of(
            execution("a", ExecutionState.SUCCEEDED, TechnicalStatus.SUCCESS, 100),
            execution("b", ExecutionState.SUCCEEDED, TechnicalStatus.SUCCESS, 200),
            execution("c", ExecutionState.FAILED, TechnicalStatus.FAILURE, 300),
            execution("d", ExecutionState.SUCCEEDED, TechnicalStatus.SUCCESS, 400));
    SliResult result =
        calculate(
            definition(
                ProvisionalSliCalculator.EXECUTION_LATENCY_P95_MS,
                HealthDimensionCode.EXECUTION_LATENCY,
                "ms",
                false),
            executions);

    assertEquals(400d, result.value());
    assertEquals(200d, result.statistics().get("p50"));
    assertEquals(400d, result.statistics().get("max"));
  }

  @Test
  void zeroSampleIsInsufficientInsteadOfPerfect() {
    SliResult result =
        calculate(
            definition(
                ProvisionalSliCalculator.EXECUTION_TECHNICAL_RELIABILITY,
                HealthDimensionCode.EXECUTION_FLOW,
                "ratio",
                true),
            List.of());

    assertEquals(SliStatus.INSUFFICIENT_DATA, result.status());
    assertNull(result.value());
  }

  @Test
  void calculatesReliabilityErrorBudgetConsumption() {
    SliResult result =
        new SliResult(
            1,
            "ratio",
            HealthDimensionCode.EXECUTION_FLOW,
            SliStatus.AVAILABLE,
            0.98,
            "ratio",
            100,
            null,
            "");
    ProvisionalSloObjective objective =
        new ProvisionalSloObjective("slo", "ratio", 0.99, null, true, 0.9);

    ErrorBudgetEvaluation budget =
        new ProvisionalSloEvaluator().evaluateErrorBudget(result, objective);

    assertEquals(ErrorBudgetStatus.EXHAUSTED, budget.status());
    assertEquals(2d, budget.consumedRatio(), 0.000001);
  }

  private SliResult calculate(
      SliDefinition definition, List<ExecutionControlRecord> executions) {
    return calculator
        .calculate(
            List.of(definition),
            new OperationalHealthData(executions, List.of(), List.of(), List.of()),
            Duration.ofMinutes(5))
        .getFirst();
  }

  private static SliDefinition definition(
      String code, HealthDimensionCode dimension, String unit, boolean higherIsBetter) {
    return new SliDefinition(
        1, code, 1, code, code, dimension, unit, 1, higherIsBetter, higherIsBetter);
  }

  private static ExecutionControlRecord execution(
      String id, ExecutionState state, TechnicalStatus technicalStatus, long durationMs) {
    return new ExecutionControlRecord(
        id,
        "ctx-" + id,
        "corr-" + id,
        "plan",
        "route",
        "1",
        state,
        1,
        technicalStatus,
        NOW.minusMillis(durationMs),
        NOW,
        NOW,
        null,
        "retention:test",
        null);
  }
}
