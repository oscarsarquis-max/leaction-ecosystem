package br.com.banco.spider.governance;

import br.com.banco.spider.execution.callback.CallbackDefinition;
import br.com.banco.spider.execution.callback.CallbackDeliveryPolicy;
import br.com.banco.spider.execution.callback.CallbackReconciliationPolicy;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.signal.ExternalSignalDefinition;
import br.com.banco.spider.execution.wait.WaitPolicyDefinition;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Optional;

/** Snapshot imutável compilado — tipos de domínio fechados apenas. */
public record ActiveGovernanceSnapshot(
    String snapshotId,
    String bundleRef,
    String bundleDigest,
    GovernanceScope governanceScope,
    Instant compiledAt,
    Map<String, RouteDefinition> routeDefinitions,
    Map<String, RetryPolicyDefinition> retryPolicies,
    Map<String, WaitPolicyDefinition> waitPolicies,
    Map<String, CallbackDefinition> callbackDefinitions,
    Map<String, CallbackDeliveryPolicy> callbackDeliveryPolicies,
    Map<String, CallbackReconciliationPolicy> callbackReconciliationPolicies,
    Map<String, IntegrityProfileDefinition> integrityProfiles,
    Map<String, BindingDescriptor> bindingDescriptors,
    Map<String, ExternalSignalDefinition> externalSignalDefinitions,
    Map<String, DataProtectionProfileDefinition> dataProtectionProfiles,
    String snapshotDigest) {

  public ActiveGovernanceSnapshot {
    Objects.requireNonNull(snapshotId, "snapshotId");
    Objects.requireNonNull(bundleRef, "bundleRef");
    Objects.requireNonNull(bundleDigest, "bundleDigest");
    Objects.requireNonNull(governanceScope, "governanceScope");
    Objects.requireNonNull(compiledAt, "compiledAt");
    Objects.requireNonNull(snapshotDigest, "snapshotDigest");
    routeDefinitions = Map.copyOf(routeDefinitions == null ? Map.of() : routeDefinitions);
    retryPolicies = Map.copyOf(retryPolicies == null ? Map.of() : retryPolicies);
    waitPolicies = Map.copyOf(waitPolicies == null ? Map.of() : waitPolicies);
    callbackDefinitions = Map.copyOf(callbackDefinitions == null ? Map.of() : callbackDefinitions);
    callbackDeliveryPolicies =
        Map.copyOf(callbackDeliveryPolicies == null ? Map.of() : callbackDeliveryPolicies);
    callbackReconciliationPolicies =
        Map.copyOf(
            callbackReconciliationPolicies == null ? Map.of() : callbackReconciliationPolicies);
    integrityProfiles = Map.copyOf(integrityProfiles == null ? Map.of() : integrityProfiles);
    bindingDescriptors = Map.copyOf(bindingDescriptors == null ? Map.of() : bindingDescriptors);
    externalSignalDefinitions =
        Map.copyOf(externalSignalDefinitions == null ? Map.of() : externalSignalDefinitions);
    dataProtectionProfiles =
        Map.copyOf(dataProtectionProfiles == null ? Map.of() : dataProtectionProfiles);
  }

  /** Compat V1 (sem DP profiles). */
  public ActiveGovernanceSnapshot(
      String snapshotId,
      String bundleRef,
      String bundleDigest,
      GovernanceScope governanceScope,
      Instant compiledAt,
      Map<String, RouteDefinition> routeDefinitions,
      Map<String, RetryPolicyDefinition> retryPolicies,
      Map<String, WaitPolicyDefinition> waitPolicies,
      Map<String, CallbackDefinition> callbackDefinitions,
      Map<String, CallbackDeliveryPolicy> callbackDeliveryPolicies,
      Map<String, CallbackReconciliationPolicy> callbackReconciliationPolicies,
      Map<String, IntegrityProfileDefinition> integrityProfiles,
      Map<String, BindingDescriptor> bindingDescriptors,
      Map<String, ExternalSignalDefinition> externalSignalDefinitions,
      String snapshotDigest) {
    this(
        snapshotId,
        bundleRef,
        bundleDigest,
        governanceScope,
        compiledAt,
        routeDefinitions,
        retryPolicies,
        waitPolicies,
        callbackDefinitions,
        callbackDeliveryPolicies,
        callbackReconciliationPolicies,
        integrityProfiles,
        bindingDescriptors,
        externalSignalDefinitions,
        Map.of(),
        snapshotDigest);
  }

  public static ActiveGovernanceSnapshot empty(GovernanceScope scope, Instant now) {
    return new ActiveGovernanceSnapshot(
        "snapshot-empty",
        "EMPTY@0",
        "empty",
        scope,
        now,
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        Map.of(),
        "empty");
  }

  public boolean hasDataProtectionProfiles() {
    return !dataProtectionProfiles.isEmpty();
  }

  public Optional<RouteDefinition> route(String exactRef) {
    return Optional.ofNullable(routeDefinitions.get(exactRef));
  }

  public Optional<BindingDescriptor> binding(String exactRef) {
    return Optional.ofNullable(bindingDescriptors.get(exactRef));
  }

  public Optional<ExternalSignalDefinition> externalSignal(String exactRef) {
    return Optional.ofNullable(externalSignalDefinitions.get(exactRef));
  }

  public Optional<DataProtectionProfileDefinition> dataProtectionProfile(String exactRef) {
    return Optional.ofNullable(dataProtectionProfiles.get(exactRef));
  }

  public List<RouteDefinition> publishedRoutes() {
    return routeDefinitions.values().stream().toList();
  }

  /** Contagem canônica para digest — dp só quando N>0 (V1 compat). */
  public String digestCounts() {
    String counts =
        "routes="
            + routeDefinitions.size()
            + ";retries="
            + retryPolicies.size()
            + ";waits="
            + waitPolicies.size()
            + ";callbacks="
            + callbackDefinitions.size()
            + ";bindings="
            + bindingDescriptors.size();
    if (!externalSignalDefinitions.isEmpty()) {
      counts = counts + ";signals=" + externalSignalDefinitions.size();
    }
    if (!dataProtectionProfiles.isEmpty()) {
      counts = counts + ";dp=" + dataProtectionProfiles.size();
    }
    return counts;
  }
}
