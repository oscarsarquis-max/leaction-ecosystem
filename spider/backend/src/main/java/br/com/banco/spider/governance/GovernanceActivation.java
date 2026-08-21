package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.Objects;

public record GovernanceActivation(
    String scopeCode,
    String activeSnapshotId,
    String previousSnapshotId,
    long activationSequence,
    Instant activatedAt,
    String activatedByPrincipalRef,
    String reasonCode,
    long optimisticVersion) {

  public GovernanceActivation {
    Objects.requireNonNull(scopeCode, "scopeCode");
    Objects.requireNonNull(activeSnapshotId, "activeSnapshotId");
    Objects.requireNonNull(activatedAt, "activatedAt");
    Objects.requireNonNull(activatedByPrincipalRef, "activatedByPrincipalRef");
    Objects.requireNonNull(reasonCode, "reasonCode");
  }
}
