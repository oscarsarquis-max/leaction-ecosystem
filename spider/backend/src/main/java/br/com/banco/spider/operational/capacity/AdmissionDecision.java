package br.com.banco.spider.operational.capacity;

import java.time.Instant;
import java.util.Objects;

/**
 * Decisão de admissão registrada.
 *
 * <p>Em modo observação {@code result} é sempre {@link AdmissionResult#ADMITTED} e {@code
 * monitorOnly} é verdadeiro; o desfecho que <em>teria</em> sido aplicado fica em {@code reasonCode},
 * prefixado por {@value #MONITOR_ONLY_PREFIX}.
 */
public record AdmissionDecision(
    String decisionId,
    Instant requestedAt,
    Instant decidedAt,
    AdmissionResult result,
    String reasonCode,
    String policyRef,
    String policyVersion,
    CapacityScopeType scopeType,
    String scopeRef,
    ShedReason shedReason,
    boolean monitorOnly,
    String correlationRef) {

  public static final String MONITOR_ONLY_PREFIX = "MONITOR_ONLY_";
  public static final String NO_POLICY_MATCH = "NO_POLICY_MATCH";
  public static final String MONITOR_BYPASS = "MONITOR_BYPASS";
  public static final String POLICY_DISABLED = "POLICY_DISABLED";
  public static final String ADMITTED = "ADMITTED";

  public AdmissionDecision {
    Objects.requireNonNull(decisionId, "decisionId");
    Objects.requireNonNull(decidedAt, "decidedAt");
    Objects.requireNonNull(result, "result");
    reasonCode = reasonCode == null ? result.name() : reasonCode;
    scopeType = scopeType == null ? CapacityScopeType.GLOBAL : scopeType;
    scopeRef =
        scopeRef == null || scopeRef.isBlank() ? CapacityScopeType.GLOBAL_SCOPE_REF : scopeRef;
  }

  public String scopeKey() {
    return CapacityScopeKey.of(scopeType, scopeRef);
  }

  /** Verdadeiro quando o chamador deve seguir adiante — inclusive sob observação. */
  public boolean allowsWork() {
    return result.admitted() || monitorOnly;
  }
}
