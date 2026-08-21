package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.wait.WaitPolicyCatalogPort;
import br.com.banco.spider.execution.wait.WaitPolicyDefinition;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.Optional;

public final class SnapshotBackedWaitPolicyCatalog implements WaitPolicyCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedWaitPolicyCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Optional<WaitPolicyDefinition> findPublished(String policyCode, String version) {
    return Optional.ofNullable(snapshot.waitPolicies().get(policyCode + "@" + version));
  }

  @Override
  public Optional<WaitPolicyDefinition> findByRef(String policyRef) {
    if (policyRef == null || policyRef.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(snapshot.waitPolicies().get(policyRef.trim()));
  }
}
