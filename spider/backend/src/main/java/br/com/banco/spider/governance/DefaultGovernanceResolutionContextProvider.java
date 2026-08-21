package br.com.banco.spider.governance;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.execution.callback.CallbackDeliveryPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQueryPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.port.ActiveGovernanceSnapshotProviderPort;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.governance.port.GovernanceActivationStorePort;
import br.com.banco.spider.governance.port.GovernanceResolutionContextProvider;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class DefaultGovernanceResolutionContextProvider
    implements GovernanceResolutionContextProvider {

  private static final Logger log =
      LoggerFactory.getLogger(DefaultGovernanceResolutionContextProvider.class);

  private final GovernanceMode mode;
  private final boolean controlPlaneEnabled;
  private final GovernanceScope scope;
  private final ActiveGovernanceSnapshotProviderPort snapshotProvider;
  private final GovernanceActivationStorePort activationStore;
  private final GovernanceSnapshotStorePort snapshotStore;
  private final ExecutionGovernanceFixationStorePort fixationStore;
  private final UniversalAdapterPort mockAdapter;
  private final ObjectProvider<CallbackDeliveryPort> mockCallbackDelivery;
  private final ObjectProvider<CallbackDeliveryStatusQueryPort> mockStatusQuery;
  private final SpiderClock clock;

  public DefaultGovernanceResolutionContextProvider(
      @Value("${spider.governance.mode:STATIC}") String mode,
      @Value("${spider.governance.control-plane.enabled:false}") boolean controlPlaneEnabled,
      @Value("${spider.governance.scope:DEFAULT}") String scopeCode,
      ActiveGovernanceSnapshotProviderPort snapshotProvider,
      GovernanceActivationStorePort activationStore,
      GovernanceSnapshotStorePort snapshotStore,
      ExecutionGovernanceFixationStorePort fixationStore,
      UniversalAdapterPort mockAdapter,
      ObjectProvider<CallbackDeliveryPort> mockCallbackDelivery,
      ObjectProvider<CallbackDeliveryStatusQueryPort> mockStatusQuery,
      SpiderClock clock) {
    this.mode = GovernanceMode.valueOf(mode.trim().toUpperCase());
    this.controlPlaneEnabled = controlPlaneEnabled;
    this.scope = new GovernanceScope(scopeCode);
    this.snapshotProvider = snapshotProvider;
    this.activationStore = activationStore;
    this.snapshotStore = snapshotStore;
    this.fixationStore = fixationStore;
    this.mockAdapter = mockAdapter;
    this.mockCallbackDelivery = mockCallbackDelivery;
    this.mockStatusQuery = mockStatusQuery;
    this.clock = clock;
  }

  public boolean isControlPlaneActive() {
    return mode == GovernanceMode.CONTROL_PLANE && controlPlaneEnabled;
  }

  @Override
  public Mono<GovernanceResolutionContext> resolveForNewExecution(
      CanonicalExecutionRequest request) {
    if (!isControlPlaneActive()) {
      return Mono.error(new IllegalStateException("CONTROL_PLANE_DISABLED"));
    }
    return Mono.fromCallable(
            () ->
                activationStore
                    .findActive(scope)
                    .orElseThrow(() -> new IllegalStateException("NO_ACTIVE_SNAPSHOT")))
        .subscribeOn(Schedulers.boundedElastic())
        .flatMap(
            activation ->
                snapshotProvider
                    .getSnapshot(activation.activeSnapshotId())
                    .map(
                        snap -> {
                          log.info(
                              "event=governance_context_resolved snapshotId={} reasonCode=NEW_EXECUTION",
                              snap.snapshotId());
                          return GovernanceResolutionContextFactory.from(
                              snap,
                              activation.activationSequence(),
                              mockAdapter,
                              mockCallbackDelivery.getIfAvailable(),
                              mockStatusQuery.getIfAvailable());
                        }));
  }

  @Override
  public Mono<GovernanceResolutionContext> resolveForExistingExecution(String executionId) {
    return Mono.fromCallable(
            () -> {
              ExecutionGovernanceFixation fixation =
                  fixationStore
                      .findByExecutionId(executionId)
                      .orElseThrow(() -> new IllegalStateException("FIXATION_NOT_FOUND"));
              ActiveGovernanceSnapshot snap =
                  snapshotStore
                      .findSnapshotById(fixation.snapshotId())
                      .orElseThrow(() -> new IllegalStateException("HISTORICAL_SNAPSHOT_MISSING"));
              if (!fixation.snapshotDigest().equals(snap.snapshotDigest())) {
                throw new IllegalStateException("FIXATION_DIGEST_MISMATCH");
              }
              log.info(
                  "event=historical_snapshot_loaded snapshotId={} reasonCode=RESUME",
                  snap.snapshotId());
              return GovernanceResolutionContextFactory.from(
                  snap,
                  fixation.activationSequence(),
                  mockAdapter,
                  mockCallbackDelivery.getIfAvailable(),
                  mockStatusQuery.getIfAvailable());
            })
        .subscribeOn(Schedulers.boundedElastic());
  }

  public ExecutionGovernanceFixation buildFixation(
      String executionId, GovernanceResolutionContext ctx) {
    String[] parts = ctx.bundleRef().split("@", 2);
    return new ExecutionGovernanceFixation(
        executionId,
        GovernanceMode.CONTROL_PLANE,
        ctx.governanceScope().code(),
        ctx.snapshotId(),
        parts[0],
        parts.length > 1 ? parts[1] : "0",
        ctx.bundleDigest(),
        ctx.snapshotDigest(),
        ctx.activationSequence(),
        clock.now());
  }

  public Optional<ExecutionGovernanceFixation> findFixation(String executionId) {
    return fixationStore.findByExecutionId(executionId);
  }

  public void persistFixation(ExecutionGovernanceFixation fixation) {
    fixationStore.insert(fixation);
  }
}
