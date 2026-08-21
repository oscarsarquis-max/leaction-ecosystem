package br.com.banco.spider.execution.wait;

import java.time.Duration;
import java.util.List;
import java.util.Objects;

public record WaitPolicyDefinition(
    String policyCode,
    String version,
    WaitType waitType,
    String acceptedSignalContractRef,
    List<String> acceptedSourceRefs,
    Duration maxWait,
    String deduplicationPolicyRef,
    String securityProfileRef,
    WaitExpiryAction expiryAction,
    WaitPolicyStatus status,
    String signalDefinitionRef) {

  public WaitPolicyDefinition {
    policyCode = Objects.requireNonNull(policyCode, "policyCode").trim();
    version = Objects.requireNonNull(version, "version").trim();
    Objects.requireNonNull(waitType, "waitType");
    acceptedSignalContractRef =
        Objects.requireNonNull(acceptedSignalContractRef, "acceptedSignalContractRef").trim();
    acceptedSourceRefs =
        acceptedSourceRefs == null ? List.of() : List.copyOf(acceptedSourceRefs);
    Objects.requireNonNull(maxWait, "maxWait");
    Objects.requireNonNull(expiryAction, "expiryAction");
    Objects.requireNonNull(status, "status");
    if (maxWait.isNegative() || maxWait.isZero()) {
      throw new IllegalArgumentException("maxWait must be positive");
    }
    if (maxWait.compareTo(Duration.ofHours(24)) > 0) {
      throw new IllegalArgumentException("maxWait exceeds configured upper bound (24h)");
    }
    deduplicationPolicyRef = blankToNull(deduplicationPolicyRef);
    securityProfileRef = blankToNull(securityProfileRef);
    signalDefinitionRef = blankToNull(signalDefinitionRef);
  }

  /** Compat: factories antigas sem signal definition. */
  public WaitPolicyDefinition(
      String policyCode,
      String version,
      WaitType waitType,
      String acceptedSignalContractRef,
      List<String> acceptedSourceRefs,
      Duration maxWait,
      String deduplicationPolicyRef,
      String securityProfileRef,
      WaitExpiryAction expiryAction,
      WaitPolicyStatus status) {
    this(
        policyCode,
        version,
        waitType,
        acceptedSignalContractRef,
        acceptedSourceRefs,
        maxWait,
        deduplicationPolicyRef,
        securityProfileRef,
        expiryAction,
        status,
        null);
  }

  public String ref() {
    return "policy:wait:" + policyCode + "@" + version;
  }

  public static WaitPolicyDefinition publishedAsync(
      String code, String version, Duration maxWait, List<String> sources) {
    return new WaitPolicyDefinition(
        code,
        version,
        WaitType.ASYNC_COMPLETION,
        "contract:signal:async-completion@1.0",
        sources,
        maxWait,
        "policy:dedup:default@1.0",
        "profile:signal:test@1.0",
        WaitExpiryAction.TIME_OUT_EXECUTION,
        WaitPolicyStatus.PUBLISHED,
        null);
  }

  public static WaitPolicyDefinition publishedUnknown(
      String code, String version, Duration maxWait, List<String> sources) {
    return new WaitPolicyDefinition(
        code,
        version,
        WaitType.UNKNOWN_OUTCOME_RECONCILIATION,
        "contract:signal:unknown-reconciliation@1.0",
        sources,
        maxWait,
        "policy:dedup:default@1.0",
        "profile:signal:test@1.0",
        WaitExpiryAction.OPEN_RECONCILIATION,
        WaitPolicyStatus.PUBLISHED,
        null);
  }

  private static String blankToNull(String v) {
    if (v == null || v.isBlank()) {
      return null;
    }
    return v.trim();
  }
}
