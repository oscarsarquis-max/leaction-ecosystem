package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.Objects;

public record ExecutionGovernanceFixation(
    String executionId,
    GovernanceMode governanceMode,
    String governanceScope,
    String snapshotId,
    String bundleCode,
    String bundleVersion,
    String bundleDigest,
    String snapshotDigest,
    long activationSequence,
    Instant fixedAt) {

  public ExecutionGovernanceFixation {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(governanceMode, "governanceMode");
    Objects.requireNonNull(governanceScope, "governanceScope");
    Objects.requireNonNull(snapshotId, "snapshotId");
    Objects.requireNonNull(bundleCode, "bundleCode");
    Objects.requireNonNull(bundleVersion, "bundleVersion");
    Objects.requireNonNull(bundleDigest, "bundleDigest");
    Objects.requireNonNull(snapshotDigest, "snapshotDigest");
    Objects.requireNonNull(fixedAt, "fixedAt");
  }

  public String governanceBundleRef() {
    return bundleCode + "@" + bundleVersion;
  }

  /** Compatibilidade com campos do Prompt 010. */
  public String governanceSnapshotId() {
    return snapshotId;
  }

  public String governanceBundleDigest() {
    return bundleDigest;
  }

  public long governanceActivationSequence() {
    return activationSequence;
  }
}
