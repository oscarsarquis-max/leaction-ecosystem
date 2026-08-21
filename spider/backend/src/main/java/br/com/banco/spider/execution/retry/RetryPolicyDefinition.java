package br.com.banco.spider.execution.retry;

import br.com.banco.spider.canonical.error.ErrorCategory;
import java.time.Duration;
import java.util.Objects;
import java.util.Set;

public record RetryPolicyDefinition(
    String policyCode,
    String version,
    int maxAttempts,
    Duration initialBackoff,
    double multiplier,
    Duration maxBackoff,
    Set<ErrorCategory> retryableCategories,
    Set<String> retryableCodes,
    Duration totalBudget,
    RetryPolicyStatus status) {

  public RetryPolicyDefinition {
    policyCode = Objects.requireNonNull(policyCode, "policyCode").trim();
    version = Objects.requireNonNull(version, "version").trim();
    Objects.requireNonNull(initialBackoff, "initialBackoff");
    Objects.requireNonNull(maxBackoff, "maxBackoff");
    Objects.requireNonNull(status, "status");
    if (maxAttempts < 1 || maxAttempts > 10) {
      throw new IllegalArgumentException("maxAttempts must be between 1 and 10");
    }
    if (initialBackoff.isNegative() || initialBackoff.isZero()) {
      throw new IllegalArgumentException("initialBackoff must be positive");
    }
    if (maxBackoff.isNegative() || maxBackoff.isZero()) {
      throw new IllegalArgumentException("maxBackoff must be positive");
    }
    if (!Double.isFinite(multiplier) || multiplier < 1.0 || multiplier > 10.0) {
      throw new IllegalArgumentException("multiplier must be finite in [1.0, 10.0]");
    }
    retryableCategories =
        retryableCategories == null ? Set.of() : Set.copyOf(retryableCategories);
    retryableCodes = retryableCodes == null ? Set.of() : Set.copyOf(retryableCodes);
  }

  public String ref() {
    return "policy:retry:" + policyCode + "@" + version;
  }

  public Duration backoffForAttempt(int attemptNumberJustCompleted) {
    double factor = Math.pow(multiplier, Math.max(0, attemptNumberJustCompleted - 1));
    long millis = Math.round(initialBackoff.toMillis() * factor);
    Duration raw = Duration.ofMillis(Math.max(1, millis));
    return raw.compareTo(maxBackoff) > 0 ? maxBackoff : raw;
  }

  public static RetryPolicyDefinition noRetry(String code, String version) {
    return new RetryPolicyDefinition(
        code,
        version,
        1,
        Duration.ofMillis(1),
        1.0,
        Duration.ofMillis(1),
        Set.of(),
        Set.of(),
        null,
        RetryPolicyStatus.PUBLISHED);
  }

  public static RetryPolicyDefinition publishedTechnical(
      String code, String version, int maxAttempts) {
    return new RetryPolicyDefinition(
        code,
        version,
        maxAttempts,
        Duration.ofMillis(10),
        2.0,
        Duration.ofMillis(100),
        Set.of(ErrorCategory.UNAVAILABLE, ErrorCategory.TIMEOUT, ErrorCategory.INTERNAL),
        Set.of(),
        Duration.ofSeconds(5),
        RetryPolicyStatus.PUBLISHED);
  }
}
