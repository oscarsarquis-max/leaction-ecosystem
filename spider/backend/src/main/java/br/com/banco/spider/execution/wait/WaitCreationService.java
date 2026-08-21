package br.com.banco.spider.execution.wait;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.budget.ExecutionDeadline;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.plan.ExecutionPlanNode;
import br.com.banco.spider.execution.signal.continuation.ContinuationToken;
import br.com.banco.spider.execution.signal.continuation.ContinuationTokenFingerprint;
import br.com.banco.spider.execution.signal.continuation.ContinuationTokenFingerprintService;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotStorePort;
import br.com.banco.spider.integration.port.ContinuationDescriptor;
import br.com.banco.spider.integration.port.UniversalAdapterResult;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

@Service
public class WaitCreationService {

  private static final Logger log = LoggerFactory.getLogger(WaitCreationService.class);

  private final ExecutionWaitStorePort waitStore;
  private final WaitPolicyCatalogPort catalog;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final boolean continuationTokenEnabled;
  private final ObjectProvider<ContinuationTokenFingerprintService> fingerprintService;
  private final ObjectProvider<ExecutionGovernanceFixationStorePort> fixationStore;
  private final ObjectProvider<GovernanceSnapshotStorePort> snapshotStore;
  private final SecureRandom secureRandom;

  public WaitCreationService(
      ExecutionWaitStorePort waitStore,
      WaitPolicyCatalogPort catalog,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this(waitStore, catalog, ids, clock, false, emptyProvider(), emptyProvider(), emptyProvider());
  }

  @Autowired
  public WaitCreationService(
      ExecutionWaitStorePort waitStore,
      WaitPolicyCatalogPort catalog,
      IdentifierGenerator ids,
      SpiderClock clock,
      @Value("${spider.signal.continuation-token.enabled:false}") boolean continuationTokenEnabled,
      ObjectProvider<ContinuationTokenFingerprintService> fingerprintService,
      ObjectProvider<ExecutionGovernanceFixationStorePort> fixationStore,
      ObjectProvider<GovernanceSnapshotStorePort> snapshotStore) {
    this.waitStore = waitStore;
    this.catalog = catalog;
    this.ids = ids;
    this.clock = clock;
    this.continuationTokenEnabled = continuationTokenEnabled;
    this.fingerprintService = fingerprintService;
    this.fixationStore = fixationStore;
    this.snapshotStore = snapshotStore;
    this.secureRandom = new SecureRandom();
  }

  private static <T> ObjectProvider<T> emptyProvider() {
    return new ObjectProvider<>() {
      @Override
      public T getObject() {
        return null;
      }

      @Override
      public T getObject(Object... args) {
        return null;
      }

      @Override
      public T getIfAvailable() {
        return null;
      }

      @Override
      public T getIfUnique() {
        return null;
      }
    };
  }

  public record WaitCreationResult(
      boolean success,
      ExecutionWaitRecord waitRecord,
      CanonicalError error,
      String issuedContinuationToken) {
    public static WaitCreationResult ok(ExecutionWaitRecord waitRecord) {
      return new WaitCreationResult(true, waitRecord, null, null);
    }

    public static WaitCreationResult ok(ExecutionWaitRecord waitRecord, String token) {
      return new WaitCreationResult(true, waitRecord, null, token);
    }

    public static WaitCreationResult fail(CanonicalError error) {
      return new WaitCreationResult(false, null, error, null);
    }
  }

  public WaitCreationResult createFromAdapterResult(
      UniversalAdapterResult adapterResult,
      ExecutionPlanNode node,
      ExecutionDeadline executionDeadline,
      String attemptId,
      WaitType waitType) {

    if (node.waitPolicyRef() == null || node.waitPolicyRef().isBlank()) {
      return WaitCreationResult.fail(
          error("WAIT_POLICY_REQUIRED", "Async/unknown step requires waitPolicyRef"));
    }
    WaitPolicyDefinition policy = catalog.findByRef(node.waitPolicyRef()).orElse(null);
    if (policy == null || !policy.status().isEligible()) {
      return WaitCreationResult.fail(
          error("WAIT_POLICY_NOT_FOUND", "Published wait policy not found: " + node.waitPolicyRef()));
    }

    ContinuationDescriptor cont = adapterResult.continuation();
    if (waitType == WaitType.ASYNC_COMPLETION) {
      if (cont == null) {
        return WaitCreationResult.fail(
            error("CONTINUATION_REQUIRED", "ACCEPTED_ASYNC requires continuation metadata"));
      }
      if (cont.waitSignalContractRef() != null
          && !cont.waitSignalContractRef().equals(policy.acceptedSignalContractRef())) {
        return WaitCreationResult.fail(
            error(
                "CONTINUATION_CONTRACT_MISMATCH",
                "Continuation contract incompatible with wait policy"));
      }
      if (cont.sourceRef() != null
          && !policy.acceptedSourceRefs().isEmpty()
          && !policy.acceptedSourceRefs().contains(cont.sourceRef())) {
        return WaitCreationResult.fail(
            error("CONTINUATION_SOURCE_MISMATCH", "Continuation source not accepted by wait policy"));
      }
    }

    Instant now = clock.now();
    Instant policyExpiry = now.plus(policy.maxWait());
    Instant execExpiry = executionDeadline.absoluteDeadline();
    Instant contExpiry =
        cont != null && cont.expiresAt() != null ? cont.expiresAt() : policyExpiry;
    Instant expiresAt = earliest(policyExpiry, earliest(execExpiry, contExpiry));
    if (!expiresAt.isAfter(now)) {
      return WaitCreationResult.fail(
          error("WAIT_DEADLINE_INVALID", "Computed wait expiresAt is not in the future"));
    }

    WaitState initial =
        waitType == WaitType.UNKNOWN_OUTCOME_RECONCILIATION && cont == null
            ? WaitState.RECONCILIATION_REQUIRED
            : WaitState.WAITING;

    String issuedToken = null;
    String fpDigest = null;
    String fpVersion = null;
    String fpKeyRef = null;
    String fpKeyVersion = null;
    Instant tokenExpires = null;
    if (continuationTokenEnabled && waitType == WaitType.ASYNC_COMPLETION) {
      ContinuationTokenFingerprintService fps = fingerprintService.getIfAvailable();
      if (fps == null) {
        return WaitCreationResult.fail(
            error("CONTINUATION_TOKEN_PROVIDER_UNAVAILABLE", "Fingerprint service unavailable"));
      }
      ContinuationToken token = ContinuationToken.generate(secureRandom);
      ContinuationTokenFingerprint fp = fps.legacySha(token);
      issuedToken = token.wire();
      token.zeroize();
      fpDigest = fp.digest();
      fpVersion = fp.algorithmVersion().name();
      fpKeyRef = fp.keyRef();
      fpKeyVersion = fp.keyVersion();
      tokenExpires = expiresAt;
      log.info("event=continuation_token_generated reasonCode=OK");
    }

    String waitId = ids.nextId("wait");
    String dataProtectionProfileRef =
        resolveDataProtectionProfileRef(
            adapterResult.executionId(), policy.signalDefinitionRef());
    ExecutionWaitRecord wait =
        new ExecutionWaitRecord(
            waitId,
            adapterResult.executionId(),
            node.stepId(),
            attemptId != null ? attemptId : adapterResult.attemptId(),
            waitType,
            policy.ref(),
            cont != null ? cont.externalOperationRef() : null,
            policy.acceptedSignalContractRef(),
            cont != null && cont.sourceRef() != null
                ? cont.sourceRef()
                : (policy.acceptedSourceRefs().isEmpty()
                    ? null
                    : policy.acceptedSourceRefs().getFirst()),
            initial,
            0L,
            now,
            null,
            expiresAt,
            null,
            initial == WaitState.RECONCILIATION_REQUIRED ? now : null,
            initial == WaitState.RECONCILIATION_REQUIRED ? "NO_CONTINUATION" : null,
            policy.signalDefinitionRef(),
            policy.securityProfileRef(),
            fpDigest,
            fpVersion,
            fpKeyRef,
            fpKeyVersion,
            tokenExpires,
            dataProtectionProfileRef);

    waitStore.insert(wait);
    log.info(
        "event=wait_created executionId={} stepId={} waitId={} waitType={} state={} reasonCode=OK",
        wait.executionId(),
        wait.stepId(),
        wait.waitId(),
        wait.waitType(),
        wait.state());
    if (initial == WaitState.RECONCILIATION_REQUIRED) {
      log.info(
          "event=reconciliation_required executionId={} stepId={} waitId={}",
          wait.executionId(),
          wait.stepId(),
          wait.waitId());
    }
    return WaitCreationResult.ok(wait, issuedToken);
  }

  private String resolveDataProtectionProfileRef(String executionId, String signalDefinitionRef) {
    if (signalDefinitionRef == null || signalDefinitionRef.isBlank()) {
      return null;
    }
    ExecutionGovernanceFixationStorePort fixStore = fixationStore.getIfAvailable();
    GovernanceSnapshotStorePort snapStore = snapshotStore.getIfAvailable();
    if (fixStore == null || snapStore == null) {
      return null;
    }
    return fixStore
        .findByExecutionId(executionId)
        .flatMap(f -> snapStore.findSnapshotById(f.snapshotId()))
        .flatMap(
            snap -> {
              var signal =
                  snap.externalSignal(signalDefinitionRef)
                      .or(
                          () ->
                              snap.externalSignalDefinitions().values().stream()
                                  .filter(s -> s.ref().equals(signalDefinitionRef))
                                  .findFirst());
              return signal.map(
                  br.com.banco.spider.execution.signal.ExternalSignalDefinition
                      ::dataProtectionProfileRef);
            })
        .orElse(null);
  }

  private static Instant earliest(Instant a, Instant b) {
    return a.isBefore(b) ? a : b;
  }

  private static CanonicalError error(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .message(message)
        .category(ErrorCategory.VALIDATION)
        .severity(ErrorSeverity.ERROR)
        .retryable(false)
        .build();
  }
}
