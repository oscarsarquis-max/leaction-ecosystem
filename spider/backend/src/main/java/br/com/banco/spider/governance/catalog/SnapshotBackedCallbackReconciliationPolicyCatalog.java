package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.callback.CallbackReconciliationPolicy;
import br.com.banco.spider.execution.callback.CallbackReconciliationPolicyCatalogPort;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.Optional;

public final class SnapshotBackedCallbackReconciliationPolicyCatalog
    implements CallbackReconciliationPolicyCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedCallbackReconciliationPolicyCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Optional<CallbackReconciliationPolicy> findByExactRef(String exactRef) {
    return Optional.ofNullable(snapshot.callbackReconciliationPolicies().get(exactRef));
  }
}
