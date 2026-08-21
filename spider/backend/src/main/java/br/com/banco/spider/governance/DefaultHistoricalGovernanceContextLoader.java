package br.com.banco.spider.governance;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.callback.CallbackReconciliationRecord;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.governance.port.HistoricalGovernanceContextLoader;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQueryPort;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class DefaultHistoricalGovernanceContextLoader
    implements HistoricalGovernanceContextLoader {

  private static final Logger log =
      LoggerFactory.getLogger(DefaultHistoricalGovernanceContextLoader.class);

  private final ExecutionGovernanceFixationStorePort fixationStore;
  private final GovernanceSnapshotStorePort snapshotStore;
  private final GovernanceArtifactDigestService digests;
  private final ObjectProvider<ExecutionWaitStorePort> waitStore;
  private final ObjectProvider<CallbackOutboxStorePort> outboxStore;
  private final ObjectProvider<CallbackReconciliationStorePort> reconciliationStore;
  private final UniversalAdapterPort mockAdapter;
  private final ObjectProvider<CallbackDeliveryPort> mockCallbackDelivery;
  private final ObjectProvider<CallbackDeliveryStatusQueryPort> mockStatusQuery;
  private final boolean cacheEnabled;
  private final int maxCached;
  private final Map<String, GovernanceResolutionContext> historicalCache =
      new ConcurrentHashMap<>();

  public DefaultHistoricalGovernanceContextLoader(
      ExecutionGovernanceFixationStorePort fixationStore,
      GovernanceSnapshotStorePort snapshotStore,
      GovernanceArtifactDigestService digests,
      ObjectProvider<ExecutionWaitStorePort> waitStore,
      ObjectProvider<CallbackOutboxStorePort> outboxStore,
      ObjectProvider<CallbackReconciliationStorePort> reconciliationStore,
      UniversalAdapterPort mockAdapter,
      ObjectProvider<CallbackDeliveryPort> mockCallbackDelivery,
      ObjectProvider<CallbackDeliveryStatusQueryPort> mockStatusQuery,
      @Value("${spider.governance.historical-context-cache.enabled:true}") boolean cacheEnabled,
      @Value("${spider.governance.historical-context-cache.max-snapshots:100}") int maxCached) {
    this.fixationStore = fixationStore;
    this.snapshotStore = snapshotStore;
    this.digests = digests;
    this.waitStore = waitStore;
    this.outboxStore = outboxStore;
    this.reconciliationStore = reconciliationStore;
    this.mockAdapter = mockAdapter;
    this.mockCallbackDelivery = mockCallbackDelivery;
    this.mockStatusQuery = mockStatusQuery;
    this.cacheEnabled = cacheEnabled;
    this.maxCached = Math.max(1, maxCached);
  }

  @Override
  public Mono<GovernanceResolutionContext> loadForExecution(String executionId) {
    return Mono.fromCallable(() -> loadBlocking(executionId))
        .subscribeOn(Schedulers.boundedElastic());
  }

  @Override
  public Mono<GovernanceResolutionContext> loadForWorkItem(GovernedWorkItemRef ref) {
    return Mono.fromCallable(
            () -> {
              String executionId = resolveExecutionId(ref);
              return loadBlocking(executionId);
            })
        .subscribeOn(Schedulers.boundedElastic());
  }

  private String resolveExecutionId(GovernedWorkItemRef ref) {
    return switch (ref.type()) {
      case WAIT -> {
        ExecutionWaitStorePort waits = waitStore.getIfAvailable();
        if (waits == null) {
          throw GovernanceContextException.of("GOVERNANCE_WORK_ITEM_OWNER_MISMATCH");
        }
        yield waits
            .findByWaitId(ref.workItemId())
            .map(ExecutionWaitRecord::executionId)
            .orElseThrow(
                () -> GovernanceContextException.of("GOVERNANCE_WORK_ITEM_OWNER_MISMATCH"));
      }
      case CALLBACK_OUTBOX -> {
        CallbackOutboxStorePort outboxes = outboxStore.getIfAvailable();
        if (outboxes == null) {
          throw GovernanceContextException.of("GOVERNANCE_WORK_ITEM_OWNER_MISMATCH");
        }
        yield outboxes
            .findByOutboxId(ref.workItemId())
            .map(CallbackOutboxRecord::executionId)
            .orElseThrow(
                () -> GovernanceContextException.of("GOVERNANCE_WORK_ITEM_OWNER_MISMATCH"));
      }
      case CALLBACK_RECONCILIATION -> {
        CallbackReconciliationStorePort recons = reconciliationStore.getIfAvailable();
        if (recons == null) {
          throw GovernanceContextException.of("GOVERNANCE_WORK_ITEM_OWNER_MISMATCH");
        }
        yield recons
            .findByReconciliationId(ref.workItemId())
            .map(CallbackReconciliationRecord::executionId)
            .orElseThrow(
                () -> GovernanceContextException.of("GOVERNANCE_WORK_ITEM_OWNER_MISMATCH"));
      }
      case EXECUTION_RECOVERY, STEP_ATTEMPT, INBOX_SIGNAL -> ref.workItemId();
    };
  }

  private GovernanceResolutionContext loadBlocking(String executionId) {
    ExecutionGovernanceFixation fixation =
        fixationStore
            .findByExecutionId(executionId)
            .orElseThrow(
                () -> GovernanceContextException.of("GOVERNANCE_FIXATION_NOT_FOUND"));

    if (cacheEnabled) {
      GovernanceResolutionContext cached = historicalCache.get(fixation.snapshotId());
      if (cached != null
          && cached.snapshotDigest().equals(fixation.snapshotDigest())
          && cached.bundleDigest().equals(fixation.bundleDigest())) {
        log.info("event=historical_cache_hit reasonCode=HIT");
        return cached;
      }
    }

    log.info("event=historical_cache_miss reasonCode=MISS");
    ActiveGovernanceSnapshot snap =
        snapshotStore
            .findSnapshotById(fixation.snapshotId())
            .orElseThrow(
                () -> GovernanceContextException.of("GOVERNANCE_SNAPSHOT_NOT_FOUND"));

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
    if (!snap.externalSignalDefinitions().isEmpty()) {
      counts = counts + ";signals=" + snap.externalSignalDefinitions().size();
    }
    if (!snap.dataProtectionProfiles().isEmpty()) {
      counts = counts + ";dp=" + snap.dataProtectionProfiles().size();
    }
    String expected = digests.digestSnapshot(snap.bundleRef(), snap.bundleDigest(), counts);
    if (!digests.secureEquals(expected, snap.snapshotDigest())
        || !digests.secureEquals(fixation.snapshotDigest(), snap.snapshotDigest())
        || !digests.secureEquals(fixation.bundleDigest(), snap.bundleDigest())) {
      historicalCache.remove(fixation.snapshotId());
      log.info("event=snapshot_digest_mismatch reasonCode=CORRUPTION");
      throw GovernanceContextException.of("GOVERNANCE_SNAPSHOT_DIGEST_MISMATCH");
    }

    GovernanceResolutionContext ctx =
        GovernanceResolutionContextFactory.from(
            snap,
            fixation.activationSequence(),
            mockAdapter,
            mockCallbackDelivery.getIfAvailable(),
            mockStatusQuery.getIfAvailable());

    if (cacheEnabled) {
      if (historicalCache.size() >= maxCached) {
        historicalCache.keySet().stream().findFirst().ifPresent(historicalCache::remove);
      }
      historicalCache.put(fixation.snapshotId(), ctx);
    }
    log.info(
        "event=historical_context_load_success reasonCode=OK mode={}",
        fixation.governanceMode());
    return ctx;
  }

  public void evict(String snapshotId) {
    historicalCache.remove(snapshotId);
  }
}
