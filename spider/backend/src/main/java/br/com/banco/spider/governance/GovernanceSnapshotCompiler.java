package br.com.banco.spider.governance;

import br.com.banco.spider.execution.callback.CallbackDefinition;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicy;
import br.com.banco.spider.execution.callback.CallbackReconciliationPolicy;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.wait.WaitPolicyDefinition;
import br.com.banco.spider.governance.port.GovernanceArtifactStorePort;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.StringJoiner;
import org.springframework.stereotype.Service;

@Service
public class GovernanceSnapshotCompiler {

  private final GovernanceArtifactStorePort artifactStore;
  private final GovernanceArtifactCodecRegistry codecs;
  private final GovernanceArtifactDigestService digestService;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public GovernanceSnapshotCompiler(
      GovernanceArtifactStorePort artifactStore,
      GovernanceArtifactCodecRegistry codecs,
      GovernanceArtifactDigestService digestService,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.artifactStore = artifactStore;
    this.codecs = codecs;
    this.digestService = digestService;
    this.ids = ids;
    this.clock = clock;
  }

  public ActiveGovernanceSnapshot compile(GovernanceBundle bundle) {
    Map<String, RouteDefinition> routes = new LinkedHashMap<>();
    Map<String, RetryPolicyDefinition> retries = new LinkedHashMap<>();
    Map<String, WaitPolicyDefinition> waits = new LinkedHashMap<>();
    Map<String, CallbackDefinition> callbacks = new LinkedHashMap<>();
    Map<String, CallbackDeliveryPolicy> deliveries = new LinkedHashMap<>();
    Map<String, CallbackReconciliationPolicy> reconciliations = new LinkedHashMap<>();
    Map<String, IntegrityProfileDefinition> integrity = new LinkedHashMap<>();
    Map<String, BindingDescriptor> bindings = new LinkedHashMap<>();
    Map<String, br.com.banco.spider.execution.signal.ExternalSignalDefinition> signals =
        new LinkedHashMap<>();
    Map<String, DataProtectionProfileDefinition> dataProtection = new LinkedHashMap<>();

    for (GovernanceArtifactRef ref : bundle.artifactRefs()) {
      GovernanceArtifact artifact =
          artifactStore
              .findByRef(ref)
              .orElseThrow(() -> new IllegalStateException("MISSING_ARTIFACT_REF"));
      Object domain =
          codecs.decode(
              ref.artifactType(),
              artifact.canonicalContent(),
              codecs.domainClass(ref.artifactType()));
      switch (ref.artifactType()) {
        case ROUTE_DEFINITION -> routes.put(ref.exactRef(), (RouteDefinition) domain);
        case RETRY_POLICY -> retries.put(ref.exactRef(), (RetryPolicyDefinition) domain);
        case WAIT_POLICY -> waits.put(ref.exactRef(), (WaitPolicyDefinition) domain);
        case CALLBACK_DEFINITION -> callbacks.put(ref.exactRef(), (CallbackDefinition) domain);
        case CALLBACK_DELIVERY_POLICY ->
            deliveries.put(ref.exactRef(), (CallbackDeliveryPolicy) domain);
        case CALLBACK_RECONCILIATION_POLICY ->
            reconciliations.put(ref.exactRef(), (CallbackReconciliationPolicy) domain);
        case INTEGRITY_PROFILE ->
            integrity.put(ref.exactRef(), (IntegrityProfileDefinition) domain);
        case ADAPTER_BINDING_DESCRIPTOR,
            CALLBACK_BINDING_DESCRIPTOR,
            STATUS_QUERY_BINDING_DESCRIPTOR ->
            bindings.put(ref.exactRef(), (BindingDescriptor) domain);
        case EXTERNAL_SIGNAL_DEFINITION -> {
          var signal = (br.com.banco.spider.execution.signal.ExternalSignalDefinition) domain;
          signals.put(signal.ref(), signal);
        }
        case DATA_PROTECTION_PROFILE -> {
          var dp = (DataProtectionProfileDefinition) domain;
          dataProtection.put(dp.exactRef(), dp);
        }
      }
    }

    ActiveGovernanceSnapshot draft =
        new ActiveGovernanceSnapshot(
            ids.nextId("gsnap"),
            bundle.exactRef(),
            bundle.bundleDigest(),
            bundle.governanceScope(),
            clock.now(),
            routes,
            retries,
            waits,
            callbacks,
            deliveries,
            reconciliations,
            integrity,
            bindings,
            signals,
            dataProtection,
            "pending");
    String snapshotDigest =
        digestService.digestSnapshot(
            bundle.exactRef(), bundle.bundleDigest(), draft.digestCounts());
    return new ActiveGovernanceSnapshot(
        draft.snapshotId(),
        draft.bundleRef(),
        draft.bundleDigest(),
        draft.governanceScope(),
        draft.compiledAt(),
        draft.routeDefinitions(),
        draft.retryPolicies(),
        draft.waitPolicies(),
        draft.callbackDefinitions(),
        draft.callbackDeliveryPolicies(),
        draft.callbackReconciliationPolicies(),
        draft.integrityProfiles(),
        draft.bindingDescriptors(),
        draft.externalSignalDefinitions(),
        draft.dataProtectionProfiles(),
        snapshotDigest);
  }

  public String computeBundleDigest(GovernanceBundle draftWithoutDigest) {
    StringJoiner joiner = new StringJoiner("\n");
    for (GovernanceArtifactRef ref : draftWithoutDigest.artifactRefs()) {
      GovernanceArtifact a =
          artifactStore
              .findByRef(ref)
              .orElseThrow(() -> new IllegalStateException("MISSING_ARTIFACT_REF"));
      joiner.add(ref + "=" + a.contentDigest());
    }
    return digestService.digestBundle(
        draftWithoutDigest.bundleCode(),
        draftWithoutDigest.bundleVersion(),
        draftWithoutDigest.governanceScope(),
        joiner.toString());
  }
}
