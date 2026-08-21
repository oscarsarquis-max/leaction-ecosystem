package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.error.ErrorCategory;
import java.time.Duration;
import java.util.EnumSet;
import java.util.Objects;
import java.util.Set;

public record CallbackDeliveryPolicy(
    String policyCode,
    String version,
    int maxAttempts,
    Duration initialBackoff,
    double multiplier,
    Duration maxBackoff,
    Duration attemptTimeout,
    Duration totalDeliveryWindow,
    Set<ErrorCategory> retryableCategories,
    boolean deadLetterOnExhaustion,
    CallbackDefinitionStatus status) {

  public CallbackDeliveryPolicy {
    Objects.requireNonNull(policyCode, "policyCode");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(initialBackoff, "initialBackoff");
    Objects.requireNonNull(maxBackoff, "maxBackoff");
    Objects.requireNonNull(attemptTimeout, "attemptTimeout");
    Objects.requireNonNull(totalDeliveryWindow, "totalDeliveryWindow");
    Objects.requireNonNull(status, "status");
    if (maxAttempts < 1) {
      throw new IllegalArgumentException("maxAttempts must include first attempt");
    }
    retryableCategories =
        retryableCategories == null
            ? EnumSet.noneOf(ErrorCategory.class)
            : EnumSet.copyOf(retryableCategories);
  }

  public String exactRef() {
    return policyCode + "@" + version;
  }

  public boolean isEligible() {
    return status == CallbackDefinitionStatus.PUBLISHED;
  }

  public static CallbackDeliveryPolicy publishedDefault(String code, String version) {
    return new CallbackDeliveryPolicy(
        code,
        version,
        3,
        Duration.ofMillis(100),
        2.0,
        Duration.ofSeconds(2),
        Duration.ofSeconds(5),
        Duration.ofMinutes(5),
        EnumSet.of(ErrorCategory.UNAVAILABLE, ErrorCategory.TIMEOUT),
        true,
        CallbackDefinitionStatus.PUBLISHED);
  }
}
