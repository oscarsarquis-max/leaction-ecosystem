package br.com.banco.spider.operational.capacity;

import java.time.Instant;

/**
 * Pressão consolidada de um escopo. Um limite ausente aparece como {@link CapacityLimit#NO_LIMIT} e
 * nunca é lido como folga confirmada.
 */
public record PressureSnapshot(
    int schemaVersion,
    String scopeKey,
    CapacityScopeType scopeType,
    String scopeRef,
    String policyRef,
    CapacityPressureLevel level,
    int occupied,
    int capacity,
    int utilizationPercent,
    int backlogCount,
    int softBacklogLimit,
    int hardBacklogLimit,
    int quotaUsed,
    int quotaLimit,
    CircuitPhase circuitPhase,
    Instant observedAt,
    String explanation) {

  public static final int SCHEMA_VERSION = 1;

  public PressureSnapshot {
    explanation = explanation == null ? "" : explanation;
    level = level == null ? CapacityPressureLevel.UNKNOWN : level;
    circuitPhase = circuitPhase == null ? CircuitPhase.CLOSED : circuitPhase;
  }
}
