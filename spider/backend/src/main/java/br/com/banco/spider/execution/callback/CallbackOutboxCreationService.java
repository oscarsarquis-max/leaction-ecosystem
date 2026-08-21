package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.fingerprint.IdempotencyKeyHashPort;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumSet;
import java.util.Optional;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * Cria Outbox na mesma transação local da terminalização quando há callback context fixado.
 */
@Service
public class CallbackOutboxCreationService {

  private static final Logger log = LoggerFactory.getLogger(CallbackOutboxCreationService.class);

  private static final Set<ExecutionState> CALLBACK_ELIGIBLE =
      EnumSet.of(
          ExecutionState.SUCCEEDED,
          ExecutionState.PARTIALLY_SUCCEEDED,
          ExecutionState.COMPENSATED,
          ExecutionState.FAILED,
          ExecutionState.TIMED_OUT,
          ExecutionState.CANCELLED);

  private final ExecutionCallbackContextStorePort contextStore;
  private final CallbackOutboxStorePort outboxStore;
  private final CallbackDeliveryPolicyCatalogPort policyCatalog;
  private final IdempotencyKeyHashPort keyHash;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public CallbackOutboxCreationService(
      ExecutionCallbackContextStorePort contextStore,
      CallbackOutboxStorePort outboxStore,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      IdempotencyKeyHashPort keyHash,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.contextStore = contextStore;
    this.outboxStore = outboxStore;
    this.policyCatalog = policyCatalog;
    this.keyHash = keyHash;
    this.ids = ids;
    this.clock = clock;
  }

  public Optional<CallbackOutboxRecord> createIfRequired(
      CanonicalExecutionResult result, PersistedExecutionResult persisted) {
    if (result == null || persisted == null) {
      return Optional.empty();
    }
    ExecutionState state = result.state();
    if (!CALLBACK_ELIGIBLE.contains(state)
        && !(state == ExecutionState.REJECTED && contextStore.findByExecutionId(persisted.executionId()).isPresent())) {
      return Optional.empty();
    }
    Optional<ExecutionCallbackContext> ctxOpt = contextStore.findByExecutionId(persisted.executionId());
    if (ctxOpt.isEmpty()) {
      return Optional.empty();
    }
    ExecutionCallbackContext ctx = ctxOpt.get();
    Instant now = clock.now();
    Duration window =
        policyCatalog
            .findByExactRef(ctx.deliveryPolicyRef())
            .filter(CallbackDeliveryPolicy::isEligible)
            .map(CallbackDeliveryPolicy::totalDeliveryWindow)
            .orElse(Duration.ofMinutes(5));

    String logicalCallbackId = "cb-logical-" + persisted.executionId();
    String logicalKey = "cb:" + persisted.executionId() + ":" + ctx.callbackDefinitionRef();
    CallbackOutboxRecord record =
        new CallbackOutboxRecord(
            ids.nextId("outbox"),
            logicalCallbackId,
            persisted.executionId(),
            ctx.callbackDefinitionRef(),
            ctx.bindingRef(),
            ctx.callbackContractRef(),
            ctx.securityProfileRef(),
            ctx.projectionRef(),
            persisted.resultRef(),
            keyHash.hash(logicalKey),
            CallbackOutboxState.PENDING,
            now,
            now,
            now.plus(window),
            0,
            0L,
            null);
    CallbackOutboxRecord stored = outboxStore.insertIdempotent(record);
    log.info(
        "event=outbox_created executionId={} outboxId={} reasonCode=OUTBOX_PENDING",
        persisted.executionId(),
        stored.outboxId());
    return Optional.of(stored);
  }
}
