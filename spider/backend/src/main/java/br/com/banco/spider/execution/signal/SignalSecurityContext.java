package br.com.banco.spider.execution.signal;

import java.time.Instant;
import java.util.Objects;

public record SignalSecurityContext(
    String principalRef,
    String sourceRef,
    String assuranceLevel,
    Instant authenticatedAt,
    Instant expiresAt,
    String securityProfileRef,
    String evidenceRef) {

  public SignalSecurityContext {
    Objects.requireNonNull(principalRef, "principalRef");
    Objects.requireNonNull(sourceRef, "sourceRef");
    Objects.requireNonNull(authenticatedAt, "authenticatedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    Objects.requireNonNull(securityProfileRef, "securityProfileRef");
  }

  public boolean isValidAt(Instant now) {
    return !now.isBefore(authenticatedAt) && now.isBefore(expiresAt);
  }
}
