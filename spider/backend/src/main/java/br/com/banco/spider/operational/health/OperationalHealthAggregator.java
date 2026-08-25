package br.com.banco.spider.operational.health;

import java.util.List;

public class OperationalHealthAggregator {

  public HealthStatus aggregate(List<HealthDimensionStatus> dimensions) {
    if (dimensions == null || dimensions.isEmpty()) {
      return HealthStatus.INSUFFICIENT_DATA;
    }
    if (dimensions.stream().anyMatch(d -> d.status() == HealthStatus.UNHEALTHY)) {
      return HealthStatus.UNHEALTHY;
    }
    if (dimensions.stream().anyMatch(d -> d.status() == HealthStatus.DEGRADED)) {
      return HealthStatus.DEGRADED;
    }
    if (dimensions.stream().allMatch(d -> d.status() == HealthStatus.HEALTHY)) {
      return HealthStatus.HEALTHY;
    }
    if (dimensions.stream().anyMatch(d -> d.status() == HealthStatus.INSUFFICIENT_DATA)) {
      return HealthStatus.INSUFFICIENT_DATA;
    }
    return HealthStatus.UNKNOWN;
  }
}
