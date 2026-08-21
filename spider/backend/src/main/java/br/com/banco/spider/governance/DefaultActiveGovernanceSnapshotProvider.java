package br.com.banco.spider.governance;

import br.com.banco.spider.governance.port.ActiveGovernanceSnapshotProviderPort;
import br.com.banco.spider.governance.port.GovernanceActivationStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

public class DefaultActiveGovernanceSnapshotProvider
    implements ActiveGovernanceSnapshotProviderPort {

  private static final Logger log =
      LoggerFactory.getLogger(DefaultActiveGovernanceSnapshotProvider.class);

  private final GovernanceActivationStorePort activationStore;
  private final GovernanceSnapshotStorePort snapshotStore;
  private final GovernanceArtifactDigestService digestService;
  private final GovernanceScope defaultScope;
  private final boolean controlPlaneEnabled;
  private final Map<String, ActiveGovernanceSnapshot> cacheByScope = new ConcurrentHashMap<>();
  private final Map<String, ActiveGovernanceSnapshot> cacheById = new ConcurrentHashMap<>();

  public DefaultActiveGovernanceSnapshotProvider(
      GovernanceActivationStorePort activationStore,
      GovernanceSnapshotStorePort snapshotStore,
      GovernanceArtifactDigestService digestService,
      GovernanceScope defaultScope,
      boolean controlPlaneEnabled) {
    this.activationStore = activationStore;
    this.snapshotStore = snapshotStore;
    this.digestService = digestService;
    this.defaultScope = defaultScope;
    this.controlPlaneEnabled = controlPlaneEnabled;
  }

  @Override
  public Mono<ActiveGovernanceSnapshot> getActiveSnapshot(GovernanceScope scope) {
    GovernanceScope s = scope == null ? defaultScope : scope;
    ActiveGovernanceSnapshot cached = cacheByScope.get(s.code());
    if (cached != null) {
      log.info("event=snapshot_cache_hit scope={}", s.code());
      return Mono.just(cached);
    }
    return refreshActive(s);
  }

  @Override
  public Mono<ActiveGovernanceSnapshot> getSnapshot(String snapshotId) {
    ActiveGovernanceSnapshot cached = cacheById.get(snapshotId);
    if (cached != null) {
      return Mono.just(cached);
    }
    return Mono.fromCallable(() -> loadAndValidate(snapshotId))
        .subscribeOn(Schedulers.boundedElastic());
  }

  @Override
  public Mono<ActiveGovernanceSnapshot> refreshActive(GovernanceScope scope) {
    return Mono.fromCallable(
            () -> {
              log.info("event=snapshot_cache_miss scope={}", scope.code());
              if (!controlPlaneEnabled) {
                ActiveGovernanceSnapshot empty =
                    ActiveGovernanceSnapshot.empty(scope, java.time.Instant.EPOCH);
                cacheByScope.put(scope.code(), empty);
                return empty;
              }
              GovernanceActivation activation =
                  activationStore
                      .findActive(scope)
                      .orElseThrow(() -> new IllegalStateException("NO_ACTIVE_SNAPSHOT"));
              ActiveGovernanceSnapshot snap = loadAndValidate(activation.activeSnapshotId());
              cacheByScope.put(scope.code(), snap);
              cacheById.put(snap.snapshotId(), snap);
              log.info(
                  "event=snapshot_cache_refresh scope={} snapshotId={}",
                  scope.code(),
                  snap.snapshotId());
              return snap;
            })
        .subscribeOn(Schedulers.boundedElastic());
  }

  public void putAfterCommit(GovernanceScope scope, ActiveGovernanceSnapshot snapshot) {
    cacheByScope.put(scope.code(), snapshot);
    cacheById.put(snapshot.snapshotId(), snapshot);
  }

  private ActiveGovernanceSnapshot loadAndValidate(String snapshotId) {
    ActiveGovernanceSnapshot snap =
        snapshotStore
            .findSnapshotById(snapshotId)
            .orElseThrow(() -> new IllegalStateException("SNAPSHOT_NOT_FOUND"));
    String counts =
        "routes="
            + snap.routeDefinitions().size()
            + ";retries="
            + snap.retryPolicies().size()
            + ";waits="
            + snap.waitPolicies().size()
            + ";callbacks="
            + snap.callbackDefinitions().size()
            + ";bindings="
            + snap.bindingDescriptors().size();
    String expected =
        digestService.digestSnapshot(snap.bundleRef(), snap.bundleDigest(), counts);
    if (!digestService.secureEquals(expected, snap.snapshotDigest())) {
      log.info("event=snapshot_digest_mismatch reasonCode=CORRUPTION");
      throw new IllegalStateException("SNAPSHOT_DIGEST_MISMATCH");
    }
    return snap;
  }
}
