package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.persistence.ReactiveExecutionPersistenceGateway;
import br.com.banco.spider.execution.persistence.port.CallbackDeliveryAttemptStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.web.filter.TraceContextWebFilter;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Service
public class CallbackOutboxProcessor {

  private static final Logger log = LoggerFactory.getLogger(CallbackOutboxProcessor.class);

  private final CallbackOutboxStorePort outboxStore;
  private final CallbackDeliveryAttemptStorePort attemptStore;
  private final ExecutionCallbackContextStorePort contextStore;
  private final ReactiveExecutionPersistenceGateway persistence;
  private final CallbackDeliveryPolicyCatalogPort policyCatalog;
  private final CallbackDefinitionCatalogPort definitionCatalog;
  private final CallbackProjectionPort projectionPort;
  private final CallbackAuthorizationPort authorization;
  private final CallbackBindingResolverPort bindingResolver;
  private final CallbackReconciliationCreationService reconciliationCreation;
  private final CallbackIntegritySupport integritySupport;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final br.com.banco.spider.governance.GovernedRuntimeSupport governedRuntime;
  private OperationalEventPublisher events = OperationalEventPublisher.noop();

  public CallbackOutboxProcessor(
      CallbackOutboxStorePort outboxStore,
      CallbackDeliveryAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      ReactiveExecutionPersistenceGateway persistence,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      CallbackDefinitionCatalogPort definitionCatalog,
      CallbackProjectionPort projectionPort,
      CallbackAuthorizationPort authorization,
      CallbackBindingResolverPort bindingResolver,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this(
        outboxStore,
        attemptStore,
        contextStore,
        persistence,
        policyCatalog,
        definitionCatalog,
        projectionPort,
        authorization,
        bindingResolver,
        null,
        null,
        ids,
        clock,
        (br.com.banco.spider.governance.GovernedRuntimeSupport) null);
  }

  public CallbackOutboxProcessor(
      CallbackOutboxStorePort outboxStore,
      CallbackDeliveryAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      ReactiveExecutionPersistenceGateway persistence,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      CallbackDefinitionCatalogPort definitionCatalog,
      CallbackProjectionPort projectionPort,
      CallbackAuthorizationPort authorization,
      CallbackBindingResolverPort bindingResolver,
      CallbackReconciliationCreationService reconciliationCreation,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this(
        outboxStore,
        attemptStore,
        contextStore,
        persistence,
        policyCatalog,
        definitionCatalog,
        projectionPort,
        authorization,
        bindingResolver,
        reconciliationCreation,
        null,
        ids,
        clock,
        (br.com.banco.spider.governance.GovernedRuntimeSupport) null);
  }

  @org.springframework.beans.factory.annotation.Autowired
  public CallbackOutboxProcessor(
      CallbackOutboxStorePort outboxStore,
      CallbackDeliveryAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      ReactiveExecutionPersistenceGateway persistence,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      CallbackDefinitionCatalogPort definitionCatalog,
      CallbackProjectionPort projectionPort,
      CallbackAuthorizationPort authorization,
      CallbackBindingResolverPort bindingResolver,
      @org.springframework.beans.factory.annotation.Autowired(required = false)
          CallbackReconciliationCreationService reconciliationCreation,
      @org.springframework.beans.factory.annotation.Autowired(required = false)
          CallbackIntegritySupport integritySupport,
      IdentifierGenerator ids,
      SpiderClock clock,
      org.springframework.beans.factory.ObjectProvider<
              br.com.banco.spider.governance.GovernedRuntimeSupport>
          governedRuntime) {
    this(
        outboxStore,
        attemptStore,
        contextStore,
        persistence,
        policyCatalog,
        definitionCatalog,
        projectionPort,
        authorization,
        bindingResolver,
        reconciliationCreation,
        integritySupport,
        ids,
        clock,
        governedRuntime == null ? null : governedRuntime.getIfAvailable());
  }

  public CallbackOutboxProcessor(
      CallbackOutboxStorePort outboxStore,
      CallbackDeliveryAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      ReactiveExecutionPersistenceGateway persistence,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      CallbackDefinitionCatalogPort definitionCatalog,
      CallbackProjectionPort projectionPort,
      CallbackAuthorizationPort authorization,
      CallbackBindingResolverPort bindingResolver,
      CallbackReconciliationCreationService reconciliationCreation,
      CallbackIntegritySupport integritySupport,
      IdentifierGenerator ids,
      SpiderClock clock,
      br.com.banco.spider.governance.GovernedRuntimeSupport governedRuntime) {
    this.outboxStore = outboxStore;
    this.attemptStore = attemptStore;
    this.contextStore = contextStore;
    this.persistence = persistence;
    this.policyCatalog = policyCatalog;
    this.definitionCatalog = definitionCatalog;
    this.projectionPort = projectionPort;
    this.authorization = authorization;
    this.bindingResolver = bindingResolver;
    this.reconciliationCreation = reconciliationCreation;
    this.integritySupport = integritySupport;
    this.ids = ids;
    this.clock = clock;
    this.governedRuntime = governedRuntime;
  }

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setOperationalEventPublisher(OperationalEventPublisher publisher) {
    if (publisher != null) {
      this.events = publisher;
    }
  }

  public Mono<List<CallbackOutboxRecord>> findReady(Instant now, int limit) {
    return Mono.fromCallable(() -> outboxStore.findReady(now, limit));
  }

  public Mono<CallbackOutboxRecord> process(String outboxId, long expectedVersion) {
    Instant now = clock.now();
    return Mono.fromCallable(
            () -> {
              CallbackOutboxRecord current =
                  outboxStore
                      .findByOutboxId(outboxId)
                      .orElseThrow(() -> new IllegalStateException("Outbox not found"));
              if (current.expiresAt().isBefore(now) || !current.expiresAt().isAfter(now)) {
                if (current.state() == CallbackOutboxState.PENDING
                    || current.state() == CallbackOutboxState.RETRY_SCHEDULED
                    || current.state() == CallbackOutboxState.DISPATCHING) {
                  log.info("event=callback_expired outboxId={} reasonCode=EXPIRED", outboxId);
                  return outboxStore.updateState(
                      outboxId,
                      current.stateVersion(),
                      CallbackOutboxState.EXPIRED,
                      current.nextAttemptAt(),
                      current.attemptCount(),
                      "CALLBACK_EXPIRED",
                      now);
                }
              }
              CallbackOutboxState from =
                  current.state() == CallbackOutboxState.RETRY_SCHEDULED
                      ? CallbackOutboxState.RETRY_SCHEDULED
                      : CallbackOutboxState.PENDING;
              return outboxStore.claim(
                  outboxId, from, expectedVersion, CallbackOutboxState.DISPATCHING, now);
            })
        .flatMap(this::dispatchClaimed);
  }

  public Mono<Integer> recoverInterruptedDispatches(Instant now) {
    Instant lease = now.minus(Duration.ofSeconds(30));
    return Mono.fromCallable(() -> outboxStore.findInterruptedDispatching(lease))
        .flatMapMany(Flux::fromIterable)
        .flatMap(
            r ->
                Mono.fromCallable(
                    () -> {
                      log.info(
                          "event=reconciliation_required outboxId={} reasonCode=INTERRUPTED_DISPATCH",
                          r.outboxId());
                      return outboxStore.updateState(
                          r.outboxId(),
                          r.stateVersion(),
                          CallbackOutboxState.UNKNOWN,
                          r.nextAttemptAt(),
                          r.attemptCount(),
                          "DISPATCH_INTERRUPTED",
                          now);
                    }))
        .count()
        .map(Long::intValue);
  }

  private Mono<CallbackOutboxRecord> dispatchClaimed(CallbackOutboxRecord claimed) {
    if (claimed.state() == CallbackOutboxState.EXPIRED) {
      return Mono.just(claimed);
    }
    Instant now = clock.now();
    log.info("event=delivery_claimed outboxId={} reasonCode=DISPATCHING", claimed.outboxId());

    Mono<br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved> resolvedMono =
        governedRuntime == null
            ? Mono.just(
                new br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved(
                    java.util.Optional.empty(),
                    java.util.Optional.empty(),
                    br.com.banco.spider.governance.GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT))
            : governedRuntime.resolveForExecution(
                claimed.executionId(),
                br.com.banco.spider.governance.GovernedEffectType.CALLBACK_DELIVERY);

    return resolvedMono.flatMap(
        resolved -> {
          if (resolved.blocksExternalEffect()) {
            log.info(
                "event=adapter_prevented_before_effect reasonCode={} effectType=CALLBACK_DELIVERY",
                resolved.decision());
            return Mono.fromCallable(
                () ->
                    outboxStore.updateState(
                        claimed.outboxId(),
                        claimed.stateVersion(),
                        CallbackOutboxState.DEAD_LETTERED,
                        claimed.nextAttemptAt(),
                        claimed.attemptCount(),
                        "GOVERNANCE_SNAPSHOT_REVOKED",
                        now));
          }
          CallbackDeliveryPolicyCatalogPort policies = resolved.deliveryOr(policyCatalog);
          CallbackDefinitionCatalogPort definitions = resolved.callbackDefOr(definitionCatalog);
          CallbackBindingResolverPort bindings = resolved.callbackBindingOr(bindingResolver);
          return dispatchClaimedWithCatalogs(claimed, policies, definitions, bindings);
        })
        .onErrorResume(
            br.com.banco.spider.governance.GovernanceContextException.class,
            ex -> {
              log.info(
                  "event=manual_review_due_to_missing_context reasonCode={}", ex.reasonCode());
              return Mono.fromCallable(
                  () ->
                      outboxStore.updateState(
                          claimed.outboxId(),
                          claimed.stateVersion(),
                          CallbackOutboxState.DEAD_LETTERED,
                          claimed.nextAttemptAt(),
                          claimed.attemptCount(),
                          ex.reasonCode(),
                          now));
            });
  }

  private Mono<CallbackOutboxRecord> dispatchClaimedWithCatalogs(
      CallbackOutboxRecord claimed,
      CallbackDeliveryPolicyCatalogPort policyCatalog,
      CallbackDefinitionCatalogPort definitionCatalog,
      CallbackBindingResolverPort bindingResolver) {
    Instant now = clock.now();

    Optional<ExecutionCallbackContext> ctxOpt =
        contextStore.findByExecutionId(claimed.executionId());
    if (ctxOpt.isEmpty()) {
      return Mono.fromCallable(
          () ->
              outboxStore.updateState(
                  claimed.outboxId(),
                  claimed.stateVersion(),
                  CallbackOutboxState.DEAD_LETTERED,
                  claimed.nextAttemptAt(),
                  claimed.attemptCount(),
                  "CALLBACK_CONTEXT_MISSING",
                  now));
    }
    ExecutionCallbackContext ctx = ctxOpt.get();
    CallbackDeliveryPolicy policy =
        policyCatalog
            .findByExactRef(ctx.deliveryPolicyRef())
            .filter(CallbackDeliveryPolicy::isEligible)
            .orElse(null);
    if (policy == null) {
      return Mono.fromCallable(
          () ->
              outboxStore.updateState(
                  claimed.outboxId(),
                  claimed.stateVersion(),
                  CallbackOutboxState.DEAD_LETTERED,
                  claimed.nextAttemptAt(),
                  claimed.attemptCount(),
                  "DELIVERY_POLICY_MISSING",
                  now));
    }

    return persistence
        .findResult(claimed.resultRef())
        .flatMap(
            resOpt -> {
              if (resOpt.isEmpty()) {
                return Mono.fromCallable(
                    () ->
                        outboxStore.updateState(
                            claimed.outboxId(),
                            claimed.stateVersion(),
                            CallbackOutboxState.DEAD_LETTERED,
                            claimed.nextAttemptAt(),
                            claimed.attemptCount(),
                            "RESULT_MISSING",
                            now));
              }
              return persistence
                  .loadResult(resOpt.get())
                  .flatMap(
                      result ->
                          deliverOnce(claimed, ctx, policy, result, resOpt.get().contentDigest()));
            });
  }

  private Mono<CallbackOutboxRecord> deliverOnce(
      CallbackOutboxRecord claimed,
      ExecutionCallbackContext ctx,
      CallbackDeliveryPolicy policy,
      CanonicalExecutionResult result,
      String digest) {
    Instant now = clock.now();
    int attemptNumber = claimed.attemptCount() + 1;
    String deliveryId = ids.nextId("cdel");
    Instant deadline = now.plus(policy.attemptTimeout());

    CallbackDeliveryAttempt attempt =
        new CallbackDeliveryAttempt(
            deliveryId,
            claimed.outboxId(),
            claimed.logicalCallbackId(),
            attemptNumber,
            claimed.bindingRef(),
            now,
            deadline,
            null,
            CallbackDeliveryAttemptState.RUNNING,
            CallbackDeliveryCertainty.UNKNOWN,
            null,
            null,
            null,
            List.of());
    attemptStore.insert(attempt);
    log.info(
        "event=attempt_started outboxId={} attemptNumber={} reasonCode=STARTED",
        claimed.outboxId(),
        attemptNumber);

    CallbackProjectionKind kind;
    try {
      kind = CallbackProjectionKind.valueOf(ctx.projectionRef());
    } catch (Exception ex) {
      return failTerminal(claimed, attemptNumber, deliveryId, "PROJECTION_UNKNOWN", now, false);
    }

    CallbackDefinition def =
        definitionCatalog.findByExactRef(ctx.callbackDefinitionRef()).orElse(null);
    if (def == null || !def.isEligible()) {
      return failTerminal(claimed, attemptNumber, deliveryId, "CALLBACK_DEF_MISSING", now, false);
    }

    return authorization
        .authorize(
            new CallbackAuthorizationRequest(
                def,
                null,
                ctx.authorizedOriginatorRef(),
                result.state().name(),
                result.outcome() != null && result.outcome().technicalStatus() != null
                    ? result.outcome().technicalStatus().name()
                    : null,
                List.of(def.maximumDataClassification()),
                ctx.projectionRef()))
        .flatMap(
            decision -> {
              if (decision != br.com.banco.spider.application.security.AuthorizationDecision.PERMIT) {
                return failTerminal(
                    claimed, attemptNumber, deliveryId, "CALLBACK_AUTHZ_DENIED", now, false);
              }
              return projectionPort
                  .project(kind, result, def.maximumDataClassification())
                  .flatMap(
                      payload ->
                          bindingResolver
                              .resolve(claimed.bindingRef())
                              .flatMap(
                                  portOpt -> {
                                    if (portOpt.isEmpty()) {
                                      return failTerminal(
                                          claimed,
                                          attemptNumber,
                                          deliveryId,
                                          "BINDING_UNKNOWN",
                                          now,
                                          false);
                                    }
                                    String logicalKey =
                                        "cb:"
                                            + claimed.executionId()
                                            + ":"
                                            + claimed.callbackDefinitionRef();
                                    java.util.function.Function<
                                            br.com.banco.spider.security.integrity.IntegrityProof,
                                            Mono<CallbackOutboxRecord>>
                                        deliverWithProof =
                                            proof -> {
                                              CallbackDeliveryEnvelope envelope =
                                                  new CallbackDeliveryEnvelope(
                                                      "1.0",
                                                      deliveryId,
                                                      claimed.logicalCallbackId(),
                                                      claimed.callbackDefinitionRef(),
                                                      claimed.executionId(),
                                                      result.trace().correlationId(),
                                                      attemptNumber,
                                                      logicalKey,
                                                      now,
                                                      new TraceDescriptor(
                                                          result.trace().correlationId(),
                                                          TraceContextWebFilter
                                                              .generateTraceparent(),
                                                          null),
                                                      payload,
                                                      proof);
                                              return portOpt
                                                  .get()
                                                  .deliver(envelope)
                                                  .flatMap(
                                                      deliveryResult ->
                                                          finalizeAttempt(
                                                              claimed,
                                                              policy,
                                                              attemptNumber,
                                                              deliveryId,
                                                              deliveryResult,
                                                              digest));
                                            };
                                    if (integritySupport == null || !integritySupport.enabled()) {
                                      return deliverWithProof.apply(null);
                                    }
                                    return integritySupport
                                        .signDelivery(ctx, claimed, attemptNumber, payload)
                                        .flatMap(opt -> deliverWithProof.apply(opt.orElse(null)))
                                        .onErrorResume(
                                            ex -> {
                                              log.info(
                                                  "event=callback_signing_blocked outboxId={} reasonCode=INTEGRITY_SIGNING_FAILED",
                                                  claimed.outboxId());
                                              return failTerminal(
                                                  claimed,
                                                  attemptNumber,
                                                  deliveryId,
                                                  "INTEGRITY_SIGNING_FAILED",
                                                  now,
                                                  false);
                                            });
                                  }));
            })
        .onErrorResume(
            ex ->
                failTerminal(
                    claimed, attemptNumber, deliveryId, "CALLBACK_INTERNAL", Instant.now(), true));
  }

  private Mono<CallbackOutboxRecord> finalizeAttempt(
      CallbackOutboxRecord claimed,
      CallbackDeliveryPolicy policy,
      int attemptNumber,
      String deliveryId,
      CallbackDeliveryResult deliveryResult,
      String digest) {
    Instant now = clock.now();
    CallbackDeliveryAttemptState attemptState =
        switch (deliveryResult.disposition()) {
          case DELIVERED -> CallbackDeliveryAttemptState.DELIVERED;
          case TIMED_OUT -> CallbackDeliveryAttemptState.TIMED_OUT;
          case UNKNOWN -> CallbackDeliveryAttemptState.UNKNOWN;
          default -> CallbackDeliveryAttemptState.FAILED;
        };
    attemptStore.complete(
        deliveryId,
        attemptState,
        deliveryResult.certainty(),
        now,
        deliveryResult.error() != null ? deliveryResult.error().category() : null,
        deliveryResult.error() != null ? deliveryResult.error().code() : null,
        deliveryResult.error() != null ? deliveryResult.error().retryable() : null,
        deliveryResult.evidenceRefs());
    log.info(
        "event=attempt_completed outboxId={} attemptNumber={} disposition={}",
        claimed.outboxId(),
        attemptNumber,
        deliveryResult.disposition());

    if (deliveryResult.disposition() == CallbackDeliveryDisposition.DELIVERED
        && deliveryResult.certainty() == CallbackDeliveryCertainty.UNCONFIRMED) {
      log.info(
          "event=callback_accepted_unconfirmed outboxId={} reasonCode=RECONCILIATION_REQUIRED",
          claimed.outboxId());
      return Mono.fromCallable(
              () ->
                  outboxStore.updateState(
                      claimed.outboxId(),
                      claimed.stateVersion(),
                      CallbackOutboxState.UNKNOWN,
                      now,
                      attemptNumber,
                      "ACCEPTED_UNCONFIRMED",
                      now))
          .doOnNext(updated -> maybeCreateReconciliation(updated, deliveryResult));
    }

    if (deliveryResult.disposition() == CallbackDeliveryDisposition.DELIVERED) {
      log.info("event=callback_delivered outboxId={} reasonCode=DELIVERED", claimed.outboxId());
      return Mono.fromCallable(
          () ->
              outboxStore.updateState(
                  claimed.outboxId(),
                  claimed.stateVersion(),
                  CallbackOutboxState.DELIVERED,
                  now,
                  attemptNumber,
                  null,
                  now))
          .doOnSuccess(
              updated ->
                  emitCallback(
                      updated,
                      OperationalEventType.CALLBACK_ACCEPTED,
                      OperationalEventOutcome.SUCCESS,
                      "DELIVERED"));
    }

    if (deliveryResult.disposition() == CallbackDeliveryDisposition.UNKNOWN
        || deliveryResult.certainty() == CallbackDeliveryCertainty.UNKNOWN) {
      log.info(
          "event=callback_unknown outboxId={} reasonCode=RECONCILIATION_REQUIRED",
          claimed.outboxId());
      return Mono.fromCallable(
              () ->
                  outboxStore.updateState(
                      claimed.outboxId(),
                      claimed.stateVersion(),
                      CallbackOutboxState.UNKNOWN,
                      now,
                      attemptNumber,
                      deliveryResult.error() != null ? deliveryResult.error().code() : "UNKNOWN",
                      now))
          .doOnNext(updated -> maybeCreateReconciliation(updated, deliveryResult));
    }

    boolean retryable =
        isRetryable(deliveryResult, policy) && attemptNumber < policy.maxAttempts();
    if (retryable) {
      Duration delay = computeBackoff(attemptNumber, policy);
      Instant next = now.plus(delay);
      if (next.isAfter(claimed.expiresAt())) {
        return deadLetter(claimed, attemptNumber, deliveryResult, now);
      }
      log.info(
          "event=retry_scheduled outboxId={} attemptNumber={} reasonCode=RETRY",
          claimed.outboxId(),
          attemptNumber);
      return Mono.fromCallable(
          () ->
              outboxStore.updateState(
                  claimed.outboxId(),
                  claimed.stateVersion(),
                  CallbackOutboxState.RETRY_SCHEDULED,
                  next,
                  attemptNumber,
                  deliveryResult.error() != null ? deliveryResult.error().code() : "RETRY",
                  now));
    }
    return deadLetter(claimed, attemptNumber, deliveryResult, now);
  }

  private Mono<CallbackOutboxRecord> deadLetter(
      CallbackOutboxRecord claimed,
      int attemptNumber,
      CallbackDeliveryResult deliveryResult,
      Instant now) {
    log.info(
        "event=callback_dead_lettered outboxId={} reasonCode=EXHAUSTED", claimed.outboxId());
    return Mono.fromCallable(
            () ->
                outboxStore.updateState(
                    claimed.outboxId(),
                    claimed.stateVersion(),
                    CallbackOutboxState.DEAD_LETTERED,
                    now,
                    attemptNumber,
                    deliveryResult.error() != null ? deliveryResult.error().code() : "DEAD_LETTER",
                    now))
        .doOnSuccess(
            updated ->
                emitCallback(
                    updated,
                    OperationalEventType.CALLBACK_REJECTED,
                    OperationalEventOutcome.FAILURE,
                    updated.lastErrorCode()));
  }

  private Mono<CallbackOutboxRecord> failTerminal(
      CallbackOutboxRecord claimed,
      int attemptNumber,
      String deliveryId,
      String errorCode,
      Instant now,
      boolean retryableHint) {
    attemptStore.complete(
        deliveryId,
        CallbackDeliveryAttemptState.FAILED,
        CallbackDeliveryCertainty.CONFIRMED,
        now,
        ErrorCategory.INTERNAL,
        errorCode,
        retryableHint,
        List.of());
    return Mono.fromCallable(
            () ->
                outboxStore.updateState(
                    claimed.outboxId(),
                    claimed.stateVersion(),
                    CallbackOutboxState.DEAD_LETTERED,
                    now,
                    attemptNumber,
                    errorCode,
                    now))
        .doOnSuccess(
            updated ->
                emitCallback(
                    updated,
                    OperationalEventType.CALLBACK_REJECTED,
                    OperationalEventOutcome.FAILURE,
                    errorCode));
  }

  private void emitCallback(
      CallbackOutboxRecord record,
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String reasonCode) {
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type,
            record.executionId(),
            null,
            "callback-outbox",
            outcome,
            null,
            OperationalEventAttributes.builder()
                .reasonCode(reasonCode)
                .disposition(record.state().name())
                .build()));
  }

  private void maybeCreateReconciliation(
      CallbackOutboxRecord updated, CallbackDeliveryResult deliveryResult) {
    if (reconciliationCreation == null) {
      return;
    }
    contextStore
        .findByExecutionId(updated.executionId())
        .ifPresent(
            ctx -> reconciliationCreation.createIfRequired(updated, ctx, deliveryResult));
  }

  private boolean isRetryable(CallbackDeliveryResult result, CallbackDeliveryPolicy policy) {
    if (result.disposition() == CallbackDeliveryDisposition.REJECTED) {
      return false;
    }
    if (result.error() == null) {
      return result.disposition() == CallbackDeliveryDisposition.TIMED_OUT
          || result.disposition() == CallbackDeliveryDisposition.FAILED;
    }
    if (!Boolean.TRUE.equals(result.error().retryable())) {
      return false;
    }
    return policy.retryableCategories().contains(result.error().category());
  }

  private static Duration computeBackoff(int attemptNumber, CallbackDeliveryPolicy policy) {
    double factor = Math.pow(policy.multiplier(), Math.max(0, attemptNumber - 1));
    long millis = (long) (policy.initialBackoff().toMillis() * factor);
    long capped = Math.min(millis, policy.maxBackoff().toMillis());
    return Duration.ofMillis(Math.max(1, capped));
  }
}
