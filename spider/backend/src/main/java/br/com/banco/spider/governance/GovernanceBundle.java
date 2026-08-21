package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Objects;
import java.util.Set;

public record GovernanceBundle(
    String bundleId,
    String bundleCode,
    String bundleVersion,
    GovernanceScope governanceScope,
    List<GovernanceArtifactRef> artifactRefs,
    String bundleDigest,
    GovernanceLifecycleState lifecycleState,
    String validationReportRef,
    String createdByPrincipalRef,
    Instant createdAt,
    Instant validatedAt,
    Instant publishedAt,
    Instant deprecatedAt,
    Instant retiredAt,
    Instant revokedAt,
    String reasonCode,
    long optimisticVersion) {

  public GovernanceBundle {
    Objects.requireNonNull(bundleId, "bundleId");
    Objects.requireNonNull(bundleCode, "bundleCode");
    Objects.requireNonNull(bundleVersion, "bundleVersion");
    Objects.requireNonNull(governanceScope, "governanceScope");
    Objects.requireNonNull(lifecycleState, "lifecycleState");
    Objects.requireNonNull(createdByPrincipalRef, "createdByPrincipalRef");
    Objects.requireNonNull(createdAt, "createdAt");
    List<GovernanceArtifactRef> raw = artifactRefs == null ? List.of() : artifactRefs;
    Set<String> seen = new LinkedHashSet<>();
    List<GovernanceArtifactRef> ordered = new ArrayList<>();
    for (GovernanceArtifactRef ref :
        raw.stream()
            .sorted(
                Comparator.comparing((GovernanceArtifactRef r) -> r.artifactType().name())
                    .thenComparing(GovernanceArtifactRef::artifactCode)
                    .thenComparing(GovernanceArtifactRef::artifactVersion))
            .toList()) {
      String key = ref.toString();
      if (!seen.add(key)) {
        throw new IllegalArgumentException("duplicate artifact ref in bundle");
      }
      ordered.add(ref);
    }
    artifactRefs = List.copyOf(ordered);
  }

  public String exactRef() {
    return bundleCode + "@" + bundleVersion;
  }

  public boolean isPublished() {
    return lifecycleState == GovernanceLifecycleState.PUBLISHED;
  }

  public boolean isRevoked() {
    return lifecycleState == GovernanceLifecycleState.REVOKED;
  }
}
