package br.com.banco.spider.operational.health;

import java.util.List;

public record DataQualitySummary(
    int schemaVersion,
    boolean complete,
    boolean resultLimitReached,
    List<String> availableSources,
    List<String> missingSources,
    List<String> warnings) {
  public DataQualitySummary {
    availableSources = availableSources == null ? List.of() : List.copyOf(availableSources);
    missingSources = missingSources == null ? List.of() : List.copyOf(missingSources);
    warnings = warnings == null ? List.of() : List.copyOf(warnings);
  }
}
