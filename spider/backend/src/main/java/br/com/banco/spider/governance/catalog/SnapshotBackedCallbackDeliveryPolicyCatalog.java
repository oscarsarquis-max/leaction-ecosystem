package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.callback.CallbackDeliveryPolicy;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicyCatalogPort;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.Optional;

public final class SnapshotBackedCallbackDeliveryPolicyCatalog
    implements CallbackDeliveryPolicyCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedCallbackDeliveryPolicyCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Optional<CallbackDeliveryPolicy> findByExactRef(String exactRef) {
    return Optional.ofNullable(snapshot.callbackDeliveryPolicies().get(exactRef));
  }
}
