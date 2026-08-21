package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.Objects;

public record GovernanceArtifact(
    String artifactId,
    GovernanceArtifactRef artifactRef,
    String schemaVersion,
    String canonicalContent,
    String contentDigest,
    GovernanceLifecycleState lifecycleState,
    String createdByPrincipalRef,
    Instant createdAt,
    Instant validatedAt,
    Instant publishedAt,
    Instant deprecatedAt,
    Instant retiredAt,
    Instant revokedAt,
    String lifecycleReasonCode,
    long optimisticVersion) {

  public GovernanceArtifact {
    Objects.requireNonNull(artifactId, "artifactId");
    Objects.requireNonNull(artifactRef, "artifactRef");
    Objects.requireNonNull(schemaVersion, "schemaVersion");
    Objects.requireNonNull(canonicalContent, "canonicalContent");
    Objects.requireNonNull(contentDigest, "contentDigest");
    Objects.requireNonNull(lifecycleState, "lifecycleState");
    Objects.requireNonNull(createdByPrincipalRef, "createdByPrincipalRef");
    Objects.requireNonNull(createdAt, "createdAt");
  }

  public boolean isEligibleForNewBundle() {
    return lifecycleState == GovernanceLifecycleState.PUBLISHED
        || lifecycleState == GovernanceLifecycleState.DEPRECATED;
  }

  public boolean isRevoked() {
    return lifecycleState == GovernanceLifecycleState.REVOKED;
  }
}
