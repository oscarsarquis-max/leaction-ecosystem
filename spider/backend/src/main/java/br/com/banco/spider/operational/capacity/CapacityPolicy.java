package br.com.banco.spider.operational.capacity;

import java.time.Duration;
import java.util.Objects;

/**
 * Política versionada de capacidade. Carregada de recurso versionado e imutável em runtime: a borda
 * nunca declara limite próprio.
 */
public record CapacityPolicy(
    String code,
    String version,
    CapacityScopeType scopeType,
    String scopeRef,
    CapacityPolicyState state,
    CapacityLimit limits,
    int circuitFailureThreshold,
    Duration circuitWindow,
    Duration circuitOpenDuration,
    int circuitProbeLimit,
    int precedence,
    boolean enforced) {

  public CapacityPolicy {
    code = require("code", code);
    version = require("version", version);
    Objects.requireNonNull(scopeType, "scopeType");
    scopeRef =
        scopeType == CapacityScopeType.GLOBAL
            ? CapacityScopeType.GLOBAL_SCOPE_REF
            : require("scopeRef", scopeRef);
    state = state == null ? CapacityPolicyState.MONITOR_ONLY : state;
    limits = limits == null ? CapacityLimit.unlimited() : limits;
    circuitWindow = circuitWindow == null ? Duration.ofMinutes(1) : circuitWindow;
    circuitOpenDuration = circuitOpenDuration == null ? Duration.ofSeconds(30) : circuitOpenDuration;
    if (circuitFailureThreshold < 0) {
      throw new IllegalArgumentException("circuitFailureThreshold must not be negative");
    }
    if (circuitProbeLimit < 0) {
      throw new IllegalArgumentException("circuitProbeLimit must not be negative");
    }
    if (circuitWindow.isZero() || circuitWindow.isNegative()) {
      throw new IllegalArgumentException("circuitWindow must be positive");
    }
    if (circuitOpenDuration.isNegative()) {
      throw new IllegalArgumentException("circuitOpenDuration must not be negative");
    }
    if (precedence < 0) {
      throw new IllegalArgumentException("precedence must not be negative");
    }
  }

  public String ref() {
    return code + "@" + version;
  }

  public String scopeKey() {
    return CapacityScopeKey.of(scopeType, scopeRef);
  }

  /** Disjuntor só existe quando há limiar e uma janela de prova declarados. */
  public boolean limitsCircuit() {
    return circuitFailureThreshold > 0;
  }

  public int effectiveProbeLimit() {
    return Math.max(1, circuitProbeLimit);
  }

  private static String require(String name, String value) {
    Objects.requireNonNull(value, name);
    String trimmed = value.trim();
    if (trimmed.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return trimmed;
  }
}
