package br.com.banco.spider.execution.callback;

import java.time.Duration;
import java.util.Objects;

public record CallbackReconciliationPolicy(
    String policyCode,
    String version,
    Duration initialDelay,
    int maxQueries,
    Duration initialBackoff,
    double multiplier,
    Duration maxBackoff,
    Duration queryTimeout,
    Duration totalReconciliationWindow,
    Duration destinationVisibilityGracePeriod,
    boolean reconcileOnAcceptedUnconfirmed,
    boolean reconcileOnUnknown,
    boolean allowRedeliveryAfterConfirmedAbsence,
    CallbackDefinitionStatus status) {

  public CallbackReconciliationPolicy {
    Objects.requireNonNull(policyCode, "policyCode");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(initialDelay, "initialDelay");
    Objects.requireNonNull(initialBackoff, "initialBackoff");
    Objects.requireNonNull(maxBackoff, "maxBackoff");
    Objects.requireNonNull(queryTimeout, "queryTimeout");
    Objects.requireNonNull(totalReconciliationWindow, "totalReconciliationWindow");
    Objects.requireNonNull(destinationVisibilityGracePeriod, "destinationVisibilityGracePeriod");
    Objects.requireNonNull(status, "status");
    if (maxQueries < 1) {
      throw new IllegalArgumentException("maxQueries must include first query");
    }
    if (initialDelay.isNegative()
        || initialBackoff.isNegative()
        || maxBackoff.isNegative()
        || queryTimeout.isNegative()
        || totalReconciliationWindow.isNegative()
        || destinationVisibilityGracePeriod.isNegative()) {
      throw new IllegalArgumentException("durations must be non-negative");
    }
    if (destinationVisibilityGracePeriod.compareTo(totalReconciliationWindow) > 0) {
      throw new IllegalArgumentException("grace period must fit within reconciliation window");
    }
    if (maxBackoff.compareTo(totalReconciliationWindow) > 0) {
      throw new IllegalArgumentException("maxBackoff must not exceed total window");
    }
  }

  public String exactRef() {
    return policyCode + "@" + version;
  }

  public boolean isEligible() {
    return status == CallbackDefinitionStatus.PUBLISHED;
  }

  public static CallbackReconciliationPolicy publishedDefault(String code, String version) {
    return new CallbackReconciliationPolicy(
        code,
        version,
        Duration.ofMillis(50),
        3,
        Duration.ofMillis(100),
        2.0,
        Duration.ofSeconds(2),
        Duration.ofSeconds(5),
        Duration.ofMinutes(5),
        Duration.ofMillis(100),
        true,
        true,
        false,
        CallbackDefinitionStatus.PUBLISHED);
  }
}
