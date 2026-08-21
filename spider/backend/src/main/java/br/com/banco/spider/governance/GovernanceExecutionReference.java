package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.Objects;

/** Referência interna governada — derivada da fixation, não do caller. */
public record GovernanceExecutionReference(
    String executionId,
    GovernanceMode governanceMode,
    String snapshotId,
    String bundleRef,
    String bundleDigest,
    long activationSequence,
    Instant fixedAt) {

  public GovernanceExecutionReference {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(governanceMode, "governanceMode");
    Objects.requireNonNull(snapshotId, "snapshotId");
    Objects.requireNonNull(bundleRef, "bundleRef");
    Objects.requireNonNull(bundleDigest, "bundleDigest");
    Objects.requireNonNull(fixedAt, "fixedAt");
  }

  public static GovernanceExecutionReference from(ExecutionGovernanceFixation f) {
    return new GovernanceExecutionReference(
        f.executionId(),
        f.governanceMode(),
        f.snapshotId(),
        f.governanceBundleRef(),
        f.bundleDigest(),
        f.activationSequence(),
        f.fixedAt());
  }

  @Override
  public String toString() {
    return "GovernanceExecutionReference{mode="
        + governanceMode
        + ", bundle="
        + bundleRef
        + ", seq="
        + activationSequence
        + "}";
  }
}
