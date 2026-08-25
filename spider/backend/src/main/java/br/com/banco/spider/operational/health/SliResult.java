package br.com.banco.spider.operational.health;

import java.util.Map;

public record SliResult(
    int schemaVersion,
    String code,
    HealthDimensionCode dimension,
    SliStatus status,
    Double value,
    String unit,
    long sampleSize,
    Map<String, Double> statistics,
    String explanation) {
  public SliResult {
    statistics = statistics == null ? Map.of() : Map.copyOf(statistics);
  }
}
