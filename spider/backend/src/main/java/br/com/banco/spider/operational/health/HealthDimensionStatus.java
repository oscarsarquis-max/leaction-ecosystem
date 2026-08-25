package br.com.banco.spider.operational.health;

import java.util.List;

public record HealthDimensionStatus(
    int schemaVersion,
    HealthDimensionCode dimension,
    HealthStatus status,
    List<String> sliCodes,
    String explanation) {
  public HealthDimensionStatus {
    sliCodes = sliCodes == null ? List.of() : List.copyOf(sliCodes);
  }
}
