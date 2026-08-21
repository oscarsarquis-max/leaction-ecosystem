package br.com.banco.spider.governance;

import br.com.banco.spider.execution.callback.CallbackBindingResolverPort;
import br.com.banco.spider.execution.callback.CallbackDefinitionCatalogPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicyCatalogPort;
import br.com.banco.spider.execution.callback.CallbackReconciliationPolicyCatalogPort;
import br.com.banco.spider.execution.callback.CallbackStatusQueryBindingResolver;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.route.RouteCatalogPort;
import br.com.banco.spider.execution.signal.ExternalSignalDefinitionCatalogPort;
import br.com.banco.spider.execution.wait.WaitPolicyCatalogPort;
import br.com.banco.spider.integration.binding.AdapterBindingResolverPort;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import java.util.Objects;

/** Contexto imutável de resolução — um snapshot, sem JPA. */
public record GovernanceResolutionContext(
    String snapshotId,
    String bundleRef,
    String bundleDigest,
    String snapshotDigest,
    long activationSequence,
    GovernanceScope governanceScope,
    RouteCatalogPort routeCatalog,
    RetryPolicyCatalogPort retryPolicyCatalog,
    WaitPolicyCatalogPort waitPolicyCatalog,
    CallbackDefinitionCatalogPort callbackDefinitionCatalog,
    CallbackDeliveryPolicyCatalogPort callbackDeliveryPolicyCatalog,
    CallbackReconciliationPolicyCatalogPort callbackReconciliationPolicyCatalog,
    IntegrityProfileCatalogPort integrityProfileCatalog,
    AdapterBindingResolverPort adapterBindingResolver,
    CallbackBindingResolverPort callbackBindingResolver,
    CallbackStatusQueryBindingResolver statusQueryBindingResolver,
    ExternalSignalDefinitionCatalogPort externalSignalDefinitionCatalog,
    br.com.banco.spider.security.dataprotection.DataProtectionProfileCatalogPort
        dataProtectionProfileCatalog) {

  public GovernanceResolutionContext {
    Objects.requireNonNull(snapshotId, "snapshotId");
    Objects.requireNonNull(bundleRef, "bundleRef");
    Objects.requireNonNull(bundleDigest, "bundleDigest");
    Objects.requireNonNull(snapshotDigest, "snapshotDigest");
    Objects.requireNonNull(governanceScope, "governanceScope");
    Objects.requireNonNull(routeCatalog, "routeCatalog");
    Objects.requireNonNull(retryPolicyCatalog, "retryPolicyCatalog");
    Objects.requireNonNull(waitPolicyCatalog, "waitPolicyCatalog");
    Objects.requireNonNull(callbackDefinitionCatalog, "callbackDefinitionCatalog");
    Objects.requireNonNull(callbackDeliveryPolicyCatalog, "callbackDeliveryPolicyCatalog");
    Objects.requireNonNull(callbackReconciliationPolicyCatalog, "callbackReconciliationPolicyCatalog");
    Objects.requireNonNull(integrityProfileCatalog, "integrityProfileCatalog");
    Objects.requireNonNull(adapterBindingResolver, "adapterBindingResolver");
    Objects.requireNonNull(callbackBindingResolver, "callbackBindingResolver");
    Objects.requireNonNull(statusQueryBindingResolver, "statusQueryBindingResolver");
    Objects.requireNonNull(externalSignalDefinitionCatalog, "externalSignalDefinitionCatalog");
    Objects.requireNonNull(dataProtectionProfileCatalog, "dataProtectionProfileCatalog");
  }
}
