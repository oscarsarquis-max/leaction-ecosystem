package br.com.banco.spider.application.security;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record AuthenticatedOriginator(
    String principalRef,
    String originatorId,
    String channel,
    String assuranceLevel,
    Instant authenticatedAt,
    Instant expiresAt,
    List<String> allowedCapabilityRefs,
    String securityProfileRef,
    String evidenceRef) {

  public AuthenticatedOriginator {
    Objects.requireNonNull(principalRef, "principalRef");
    Objects.requireNonNull(originatorId, "originatorId");
    Objects.requireNonNull(channel, "channel");
    Objects.requireNonNull(authenticatedAt, "authenticatedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    allowedCapabilityRefs =
        allowedCapabilityRefs == null ? List.of() : List.copyOf(allowedCapabilityRefs);
  }

  public boolean isValidAt(Instant now) {
    return !now.isBefore(authenticatedAt) && now.isBefore(expiresAt);
  }
}
