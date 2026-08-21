package br.com.banco.spider.execution.callback;

import br.com.banco.spider.execution.callback.CallbackDeliveryResult;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class CallbackReconciliationCreationService {

  private static final Logger log = LoggerFactory.getLogger(CallbackReconciliationCreationService.class);

  private final CallbackReconciliationStorePort store;
  private final CallbackReconciliationPolicyCatalogPort policyCatalog;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public CallbackReconciliationCreationService(
      CallbackReconciliationStorePort store,
      CallbackReconciliationPolicyCatalogPort policyCatalog,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.store = store;
    this.policyCatalog = policyCatalog;
    this.ids = ids;
    this.clock = clock;
  }

  public Optional<CallbackReconciliationRecord> createIfRequired(
      CallbackOutboxRecord outbox,
      ExecutionCallbackContext ctx,
      CallbackDeliveryResult deliveryResult) {
    if (outbox == null || ctx == null) {
      return Optional.empty();
    }
    if (store.findByOutboxId(outbox.outboxId()).isPresent()) {
      return store.findByOutboxId(outbox.outboxId());
    }
    CallbackConfirmationMode mode = ctx.confirmationMode();
    if (mode == CallbackConfirmationMode.SYNCHRONOUS_ACK_IS_FINAL
        && deliveryResult != null
        && deliveryResult.disposition() == CallbackDeliveryDisposition.DELIVERED
        && deliveryResult.certainty() == CallbackDeliveryCertainty.CONFIRMED) {
      return Optional.empty();
    }
    if (mode == CallbackConfirmationMode.NO_CONFIRMATION_AVAILABLE) {
      return Optional.empty();
    }
    boolean needs =
        mode == CallbackConfirmationMode.STATUS_QUERY_REQUIRED
            || (mode == CallbackConfirmationMode.STATUS_QUERY_WHEN_UNCERTAIN
                && deliveryResult != null
                && (deliveryResult.disposition() == CallbackDeliveryDisposition.UNKNOWN
                    || deliveryResult.certainty() == CallbackDeliveryCertainty.UNKNOWN
                    || deliveryResult.certainty() == CallbackDeliveryCertainty.UNCONFIRMED));
    if (!needs) {
      return Optional.empty();
    }
    if (ctx.statusQueryBindingRef() == null || ctx.reconciliationPolicyRef() == null) {
      log.info(
          "event=reconciliation_skipped outboxId={} reasonCode=NO_QUERY_BINDING",
          outbox.outboxId());
      return Optional.empty();
    }
    CallbackReconciliationPolicy policy =
        policyCatalog
            .findByExactRef(ctx.reconciliationPolicyRef())
            .filter(CallbackReconciliationPolicy::isEligible)
            .orElse(null);
    if (policy == null) {
      log.info(
          "event=reconciliation_skipped outboxId={} reasonCode=POLICY_MISSING",
          outbox.outboxId());
      return Optional.empty();
    }
    if (deliveryResult != null
        && deliveryResult.disposition() == CallbackDeliveryDisposition.UNKNOWN
        && !policy.reconcileOnUnknown()) {
      return Optional.empty();
    }
    Instant now = clock.now();
    CallbackReconciliationRecord record =
        new CallbackReconciliationRecord(
            ids.nextId("crec"),
            outbox.outboxId(),
            outbox.executionId(),
            ctx.deliveryKeyHash(),
            policy.exactRef(),
            CallbackReconciliationState.PENDING,
            0,
            now.plus(policy.initialDelay()),
            now,
            now.plus(policy.totalReconciliationWindow()),
            null,
            null,
            null,
            null,
            0L,
            now,
            now);
    CallbackReconciliationRecord stored = store.insertIdempotent(record);
    log.info(
        "event=reconciliation_created outboxId={} reconciliationId={} reasonCode=CREATED",
        outbox.outboxId(),
        stored.reconciliationId());
    return Optional.of(stored);
  }
}
