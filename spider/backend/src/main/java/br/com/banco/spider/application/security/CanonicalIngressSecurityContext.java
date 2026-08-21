package br.com.banco.spider.application.security;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record CanonicalIngressSecurityContext(
    String principalRef,
    String originatorId,
    String channel,
    String assuranceLevel,
    String authorizationDecisionRef,
    Instant authenticatedAt,
    Instant expiresAt,
    List<String> evidenceRefs) {

  public CanonicalIngressSecurityContext {
    Objects.requireNonNull(principalRef, "principalRef");
    Objects.requireNonNull(originatorId, "originatorId");
    Objects.requireNonNull(channel, "channel");
    Objects.requireNonNull(authenticatedAt, "authenticatedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }

  public static CanonicalIngressSecurityContext from(
      AuthenticatedOriginator originator, AuthorizationDecision decision) {
    return new CanonicalIngressSecurityContext(
        originator.principalRef(),
        originator.originatorId(),
        originator.channel(),
        originator.assuranceLevel(),
        decision.name(),
        originator.authenticatedAt(),
        originator.expiresAt(),
        originator.evidenceRef() == null ? List.of() : List.of(originator.evidenceRef()));
  }
}
