package br.com.banco.spider.operational.health;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.List;
import org.junit.jupiter.api.Test;

class OperationalHealthAggregatorTest {
  private final OperationalHealthAggregator aggregator = new OperationalHealthAggregator();

  @Test
  void unhealthyTakesPrecedence() {
    assertEquals(
        HealthStatus.UNHEALTHY,
        aggregator.aggregate(
            List.of(
                dimension(HealthDimensionCode.EXECUTION_FLOW, HealthStatus.HEALTHY),
                dimension(HealthDimensionCode.ASYNC_WAIT, HealthStatus.UNHEALTHY))));
  }

  @Test
  void degradedTakesPrecedenceOverInsufficientData() {
    assertEquals(
        HealthStatus.DEGRADED,
        aggregator.aggregate(
            List.of(
                dimension(HealthDimensionCode.EXECUTION_FLOW, HealthStatus.DEGRADED),
                dimension(
                    HealthDimensionCode.TELEMETRY_COVERAGE,
                    HealthStatus.INSUFFICIENT_DATA))));
  }

  @Test
  void allHealthyIsHealthyAndNoDimensionsIsInsufficient() {
    assertEquals(
        HealthStatus.HEALTHY,
        aggregator.aggregate(
            List.of(dimension(HealthDimensionCode.EXECUTION_FLOW, HealthStatus.HEALTHY))));
    assertEquals(HealthStatus.INSUFFICIENT_DATA, aggregator.aggregate(List.of()));
  }

  private static HealthDimensionStatus dimension(
      HealthDimensionCode code, HealthStatus status) {
    return new HealthDimensionStatus(1, code, status, List.of(), "");
  }
}
