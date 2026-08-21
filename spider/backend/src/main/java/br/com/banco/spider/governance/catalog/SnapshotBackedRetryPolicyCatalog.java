package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.Optional;

public final class SnapshotBackedRetryPolicyCatalog implements RetryPolicyCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedRetryPolicyCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Optional<RetryPolicyDefinition> findPublished(String policyCode, String version) {
    return Optional.ofNullable(snapshot.retryPolicies().get(policyCode + "@" + version));
  }

  @Override
  public Optional<RetryPolicyDefinition> findByRef(String policyRef) {
    if (policyRef == null || policyRef.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(snapshot.retryPolicies().get(policyRef.trim()));
  }
}
