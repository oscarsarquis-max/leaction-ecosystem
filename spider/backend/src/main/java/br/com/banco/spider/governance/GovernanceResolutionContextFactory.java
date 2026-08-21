package br.com.banco.spider.governance;

import br.com.banco.spider.execution.callback.CallbackDeliveryPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQueryPort;
import br.com.banco.spider.execution.callback.ConfiguredCallbackBindingResolver;
import br.com.banco.spider.execution.callback.ConfiguredCallbackStatusQueryBindingResolver;
import br.com.banco.spider.governance.catalog.SnapshotBackedAdapterBindingResolver;
import br.com.banco.spider.governance.catalog.SnapshotBackedCallbackBindingResolver;
import br.com.banco.spider.governance.catalog.SnapshotBackedCallbackDefinitionCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedCallbackDeliveryPolicyCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedCallbackReconciliationPolicyCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedDataProtectionProfileCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedExternalSignalDefinitionCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedIntegrityProfileCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedRetryPolicyCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedRouteCatalog;
import br.com.banco.spider.governance.catalog.SnapshotBackedStatusQueryBindingResolver;
import br.com.banco.spider.governance.catalog.SnapshotBackedWaitPolicyCatalog;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import java.util.Map;

public final class GovernanceResolutionContextFactory {

  private GovernanceResolutionContextFactory() {}

  public static GovernanceResolutionContext from(
      ActiveGovernanceSnapshot snapshot,
      long activationSequence,
      UniversalAdapterPort mockAdapter,
      CallbackDeliveryPort mockCallbackDelivery,
      CallbackDeliveryStatusQueryPort mockStatusQuery) {
    return new GovernanceResolutionContext(
        snapshot.snapshotId(),
        snapshot.bundleRef(),
        snapshot.bundleDigest(),
        snapshot.snapshotDigest(),
        activationSequence,
        snapshot.governanceScope(),
        new SnapshotBackedRouteCatalog(snapshot),
        new SnapshotBackedRetryPolicyCatalog(snapshot),
        new SnapshotBackedWaitPolicyCatalog(snapshot),
        new SnapshotBackedCallbackDefinitionCatalog(snapshot),
        new SnapshotBackedCallbackDeliveryPolicyCatalog(snapshot),
        new SnapshotBackedCallbackReconciliationPolicyCatalog(snapshot),
        new SnapshotBackedIntegrityProfileCatalog(snapshot),
        new SnapshotBackedAdapterBindingResolver(snapshot, mockAdapter),
        mockCallbackDelivery == null
            ? new ConfiguredCallbackBindingResolver(Map.of())
            : new SnapshotBackedCallbackBindingResolver(snapshot, mockCallbackDelivery),
        mockStatusQuery == null
            ? new ConfiguredCallbackStatusQueryBindingResolver(Map.of())
            : new SnapshotBackedStatusQueryBindingResolver(snapshot, mockStatusQuery),
        new SnapshotBackedExternalSignalDefinitionCatalog(snapshot),
        new SnapshotBackedDataProtectionProfileCatalog(snapshot));
  }
}
