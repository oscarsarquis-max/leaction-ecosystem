package br.com.banco.spider.execution.callback;

import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationAttemptStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Service
public class CallbackReconciliationProcessor {

  private static final Logger log = LoggerFactory.getLogger(CallbackReconciliationProcessor.class);

  public record ReconciliationBatchResult(
      int claimed, int confirmed, int retried, int exhausted, int manualReview, int failed) {}

  private final CallbackReconciliationStorePort reconciliationStore;
  private final CallbackReconciliationAttemptStorePort attemptStore;
  private final ExecutionCallbackContextStorePort contextStore;
  private final CallbackOutboxStorePort outboxStore;
  private final CallbackReconciliationPolicyCatalogPort policyCatalog;
  private final CallbackStatusQueryBindingResolver bindingResolver;
  private final CallbackRedeliveryDecisionService redeliveryDecision;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final Duration leaseDuration;
  private final br.com.banco.spider.governance.GovernedRuntimeSupport governedRuntime;

  @org.springframework.beans.factory.annotation.Autowired
  public CallbackReconciliationProcessor(
      CallbackReconciliationStorePort reconciliationStore,
      CallbackReconciliationAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      CallbackOutboxStorePort outboxStore,
      CallbackReconciliationPolicyCatalogPort policyCatalog,
      CallbackStatusQueryBindingResolver bindingResolver,
      CallbackRedeliveryDecisionService redeliveryDecision,
      IdentifierGenerator ids,
      SpiderClock clock,
      org.springframework.beans.factory.ObjectProvider<
              br.com.banco.spider.governance.GovernedRuntimeSupport>
          governedRuntime) {
    this(
        reconciliationStore,
        attemptStore,
        contextStore,
        outboxStore,
        policyCatalog,
        bindingResolver,
        redeliveryDecision,
        ids,
        clock,
        Duration.ofSeconds(30),
        governedRuntime.getIfAvailable());
  }

  public CallbackReconciliationProcessor(
      CallbackReconciliationStorePort reconciliationStore,
      CallbackReconciliationAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      CallbackOutboxStorePort outboxStore,
      CallbackReconciliationPolicyCatalogPort policyCatalog,
      CallbackStatusQueryBindingResolver bindingResolver,
      CallbackRedeliveryDecisionService redeliveryDecision,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this(
        reconciliationStore,
        attemptStore,
        contextStore,
        outboxStore,
        policyCatalog,
        bindingResolver,
        redeliveryDecision,
        ids,
        clock,
        Duration.ofSeconds(30),
        (br.com.banco.spider.governance.GovernedRuntimeSupport) null);
  }

  public CallbackReconciliationProcessor(
      CallbackReconciliationStorePort reconciliationStore,
      CallbackReconciliationAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      CallbackOutboxStorePort outboxStore,
      CallbackReconciliationPolicyCatalogPort policyCatalog,
      CallbackStatusQueryBindingResolver bindingResolver,
      CallbackRedeliveryDecisionService redeliveryDecision,
      IdentifierGenerator ids,
      SpiderClock clock,
      Duration leaseDuration) {
    this(
        reconciliationStore,
        attemptStore,
        contextStore,
        outboxStore,
        policyCatalog,
        bindingResolver,
        redeliveryDecision,
        ids,
        clock,
        leaseDuration,
        (br.com.banco.spider.governance.GovernedRuntimeSupport) null);
  }

  public CallbackReconciliationProcessor(
      CallbackReconciliationStorePort reconciliationStore,
      CallbackReconciliationAttemptStorePort attemptStore,
      ExecutionCallbackContextStorePort contextStore,
      CallbackOutboxStorePort outboxStore,
      CallbackReconciliationPolicyCatalogPort policyCatalog,
      CallbackStatusQueryBindingResolver bindingResolver,
      CallbackRedeliveryDecisionService redeliveryDecision,
      IdentifierGenerator ids,
      SpiderClock clock,
      Duration leaseDuration,
      br.com.banco.spider.governance.GovernedRuntimeSupport governedRuntime) {
    this.reconciliationStore = reconciliationStore;
    this.attemptStore = attemptStore;
    this.contextStore = contextStore;
    this.outboxStore = outboxStore;
    this.policyCatalog = policyCatalog;
    this.bindingResolver = bindingResolver;
    this.redeliveryDecision = redeliveryDecision;
    this.ids = ids;
    this.clock = clock;
    this.leaseDuration = leaseDuration;
    this.governedRuntime = governedRuntime;
  }

  public Mono<ReconciliationBatchResult> processDue(String workerId, Instant now, int batchSize) {
    List<CallbackReconciliationRecord> due = reconciliationStore.findDue(now, batchSize);
    return Flux.fromIterable(due)
        .concatMap(r -> processOne(workerId, r, now))
        .collectList()
        .map(
            outcomes -> {
              int claimed = outcomes.size();
              int confirmed = (int) outcomes.stream().filter(o -> o == Outcome.CONFIRMED).count();
              int retried = (int) outcomes.stream().filter(o -> o == Outcome.RETRIED).count();
              int exhausted = (int) outcomes.stream().filter(o -> o == Outcome.EXHAUSTED).count();
              int manual = (int) outcomes.stream().filter(o -> o == Outcome.MANUAL).count();
              int failed = (int) outcomes.stream().filter(o -> o == Outcome.FAILED).count();
              return new ReconciliationBatchResult(
                  claimed, confirmed, retried, exhausted, manual, failed);
            });
  }

  private enum Outcome {
    CONFIRMED,
    RETRIED,
    EXHAUSTED,
    MANUAL,
    FAILED,
    SKIPPED
  }

  private Mono<Outcome> processOne(
      String workerId, CallbackReconciliationRecord candidate, Instant now) {
    Optional<CallbackReconciliationRecord> claimed =
        reconciliationStore.claim(
            candidate.reconciliationId(),
            candidate.version(),
            workerId,
            now.plus(leaseDuration),
            now);
    if (claimed.isEmpty()) {
      log.info(
          "event=query_claim_lost reconciliationId={} reasonCode=LOST",
          candidate.reconciliationId());
      return Mono.just(Outcome.SKIPPED);
    }
    CallbackReconciliationRecord rec = claimed.get();
    log.info(
        "event=query_claimed reconciliationId={} reasonCode=OK", rec.reconciliationId());

    Mono<br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved> resolvedMono =
        governedRuntime == null
            ? Mono.just(
                new br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved(
                    java.util.Optional.empty(),
                    java.util.Optional.empty(),
                    br.com.banco.spider.governance.GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT))
            : governedRuntime.resolveForExecution(
                rec.executionId(),
                br.com.banco.spider.governance.GovernedEffectType.CALLBACK_STATUS_QUERY);

    return resolvedMono.flatMap(
        resolved -> {
          if (resolved.blocksExternalEffect()) {
            log.info(
                "event=adapter_prevented_before_effect reasonCode={} effectType=CALLBACK_STATUS_QUERY",
                resolved.decision());
            reconciliationStore.update(
                rec.reconciliationId(),
                rec.version(),
                CallbackReconciliationState.MANUAL_REVIEW,
                rec.queryCount(),
                rec.nextQueryAt(),
                rec.lastDisposition(),
                null,
                null,
                null,
                now);
            return Mono.just(Outcome.MANUAL);
          }
          return processOneWithCatalogs(
              rec,
              now,
              resolved.reconciliationOr(policyCatalog),
              resolved.statusQueryOr(bindingResolver));
        })
        .onErrorResume(
            br.com.banco.spider.governance.GovernanceContextException.class,
            ex -> {
              log.info(
                  "event=manual_review_due_to_missing_context reasonCode={}", ex.reasonCode());
              reconciliationStore.update(
                  rec.reconciliationId(),
                  rec.version(),
                  CallbackReconciliationState.MANUAL_REVIEW,
                  rec.queryCount(),
                  rec.nextQueryAt(),
                  rec.lastDisposition(),
                  null,
                  null,
                  null,
                  now);
              return Mono.just(Outcome.MANUAL);
            });
  }

  private Mono<Outcome> processOneWithCatalogs(
      CallbackReconciliationRecord rec,
      Instant now,
      CallbackReconciliationPolicyCatalogPort policyCatalog,
      CallbackStatusQueryBindingResolver bindingResolver) {
    if (!rec.expiresAt().isAfter(now)) {
      reconciliationStore.update(
          rec.reconciliationId(),
          rec.version(),
          CallbackReconciliationState.EXPIRED,
          rec.queryCount(),
          rec.nextQueryAt(),
          rec.lastDisposition(),
          null,
          null,
          null,
          now);
      return Mono.just(Outcome.EXHAUSTED);
    }

    Optional<ExecutionCallbackContext> ctxOpt = contextStore.findByExecutionId(rec.executionId());
    if (ctxOpt.isEmpty()) {
      return finish(rec, CallbackReconciliationState.MANUAL_REVIEW, null, Outcome.MANUAL, now);
    }
    ExecutionCallbackContext ctx = ctxOpt.get();
    CallbackReconciliationPolicy policy =
        policyCatalog.findByExactRef(rec.policyRef()).filter(CallbackReconciliationPolicy::isEligible).orElse(null);
    if (policy == null) {
      return finish(rec, CallbackReconciliationState.MANUAL_REVIEW, null, Outcome.MANUAL, now);
    }

    int attemptNumber = rec.queryCount() + 1;
    if (attemptNumber > policy.maxQueries()) {
      return finish(rec, CallbackReconciliationState.EXHAUSTED, null, Outcome.EXHAUSTED, now);
    }

    return bindingResolver
        .resolve(ctx.statusQueryBindingRef())
        .flatMap(
            portOpt -> {
              if (portOpt.isEmpty()) {
                log.info(
                    "event=query_failed reconciliationId={} reasonCode=BINDING_MISSING",
                    rec.reconciliationId());
                return finish(
                    rec, CallbackReconciliationState.MANUAL_REVIEW, null, Outcome.FAILED, now);
              }
              Instant deadline = now.plus(policy.queryTimeout());
              if (deadline.isAfter(rec.expiresAt())) {
                deadline = rec.expiresAt();
              }
              log.info(
                  "event=query_attempt_started reconciliationId={} attemptNumber={}",
                  rec.reconciliationId(),
                  attemptNumber);
              CallbackDeliveryStatusQuery query =
                  new CallbackDeliveryStatusQuery(
                      rec.executionId(),
                      ctx.callbackDefinitionRef(),
                      "cb:" + rec.executionId() + ":" + ctx.callbackDefinitionRef(),
                      null,
                      ctx.callbackContractRef(),
                      ctx.statusQueryBindingRef(),
                      ctx.securityProfileRef(),
                      attemptNumber,
                      deadline,
                      "corr-" + rec.executionId(),
                      null);
              return portOpt
                  .get()
                  .query(query)
                  .flatMap(result -> applyResult(rec, ctx, policy, attemptNumber, result, now))
                  .onErrorResume(
                      ex ->
                          finish(
                              rec,
                              CallbackReconciliationState.UNKNOWN,
                              CallbackDeliveryStatusDisposition.UNKNOWN,
                              Outcome.FAILED,
                              now));
            });
  }

  private Mono<Outcome> applyResult(
      CallbackReconciliationRecord rec,
      ExecutionCallbackContext ctx,
      CallbackReconciliationPolicy policy,
      int attemptNumber,
      CallbackDeliveryStatusQueryResult result,
      Instant now) {
    if (attemptStore.findByReconciliationAndNumber(rec.reconciliationId(), attemptNumber).isEmpty()) {
      attemptStore.insert(
          new CallbackReconciliationAttempt(
              ids.nextId("cqatt"),
              rec.reconciliationId(),
              attemptNumber,
              now,
              now,
              result.disposition(),
              result.safeProviderStatusCode(),
              result.error(),
              null,
              result.evidenceRef(),
              rec.executionId()));
    }
    log.info(
        "event=query_attempt_completed reconciliationId={} disposition={}",
        rec.reconciliationId(),
        result.disposition());

    return switch (result.disposition()) {
      case CONFIRMED_DELIVERED -> {
        log.info(
            "event=confirmed_delivered reconciliationId={} reasonCode=OK",
            rec.reconciliationId());
        yield finish(
            rec,
            CallbackReconciliationState.CONFIRMED_DELIVERED,
            result.disposition(),
            Outcome.CONFIRMED,
            now);
      }
      case CONFIRMED_REJECTED ->
          finish(
              rec,
              CallbackReconciliationState.CONFIRMED_REJECTED,
              result.disposition(),
              Outcome.EXHAUSTED,
              now);
      case PERMANENT_QUERY_FAILURE ->
          finish(
              rec,
              CallbackReconciliationState.EXHAUSTED,
              result.disposition(),
              Outcome.EXHAUSTED,
              now);
      case UNKNOWN ->
          finish(
              rec,
              CallbackReconciliationState.UNKNOWN,
              result.disposition(),
              Outcome.MANUAL,
              now);
      case CONFIRMED_NOT_FOUND -> {
        CallbackRedeliveryDecision decision =
            redeliveryDecision.decide(result.disposition(), ctx, policy, rec, now);
        yield switch (decision) {
          case WAIT_AND_QUERY_AGAIN -> scheduleRetry(rec, policy, attemptNumber, result, now);
          case REDISPATCH_ALLOWED -> {
            outboxStore
                .findByOutboxId(rec.outboxId())
                .ifPresent(
                    o ->
                        outboxStore.updateState(
                            o.outboxId(),
                            o.stateVersion(),
                            CallbackOutboxState.RETRY_SCHEDULED,
                            now,
                            o.attemptCount(),
                            "REDISPATCH_AFTER_ABSENCE",
                            now));
            yield finish(
                rec,
                CallbackReconciliationState.CONFIRMED_ABSENT,
                result.disposition(),
                Outcome.EXHAUSTED,
                now);
          }
          case FINISH_CONFIRMED_ABSENT ->
              finish(
                  rec,
                  CallbackReconciliationState.CONFIRMED_ABSENT,
                  result.disposition(),
                  Outcome.EXHAUSTED,
                  now);
          case EXPIRE ->
              finish(
                  rec,
                  CallbackReconciliationState.EXPIRED,
                  result.disposition(),
                  Outcome.EXHAUSTED,
                  now);
          case MANUAL_REVIEW_REQUIRED ->
              finish(
                  rec,
                  CallbackReconciliationState.MANUAL_REVIEW,
                  result.disposition(),
                  Outcome.MANUAL,
                  now);
        };
      }
      case ACCEPTED_NOT_FINAL, RETRYABLE_QUERY_FAILURE ->
          scheduleRetry(rec, policy, attemptNumber, result, now);
    };
  }

  private Mono<Outcome> scheduleRetry(
      CallbackReconciliationRecord rec,
      CallbackReconciliationPolicy policy,
      int attemptNumber,
      CallbackDeliveryStatusQueryResult result,
      Instant now) {
    if (attemptNumber >= policy.maxQueries()) {
      return finish(
          rec, CallbackReconciliationState.EXHAUSTED, result.disposition(), Outcome.EXHAUSTED, now);
    }
    Duration delay = computeBackoff(attemptNumber, policy);
    if (result.retryAfter() != null && result.retryAfter().compareTo(delay) > 0) {
      delay = result.retryAfter().compareTo(policy.maxBackoff()) > 0 ? policy.maxBackoff() : result.retryAfter();
    }
    Instant next = now.plus(delay);
    if (!next.isBefore(rec.expiresAt())) {
      return finish(
          rec, CallbackReconciliationState.EXPIRED, result.disposition(), Outcome.EXHAUSTED, now);
    }
    log.info(
        "event=query_retry_scheduled reconciliationId={} attemptNumber={}",
        rec.reconciliationId(),
        attemptNumber);
    reconciliationStore.update(
        rec.reconciliationId(),
        rec.version(),
        CallbackReconciliationState.RETRY_SCHEDULED,
        attemptNumber,
        next,
        result.disposition(),
        result.externalDeliveryRef(),
        null,
        null,
        now);
    return Mono.just(Outcome.RETRIED);
  }

  private Mono<Outcome> finish(
      CallbackReconciliationRecord rec,
      CallbackReconciliationState state,
      CallbackDeliveryStatusDisposition disposition,
      Outcome outcome,
      Instant now) {
    reconciliationStore.update(
        rec.reconciliationId(),
        rec.version(),
        state,
        rec.queryCount() + (state == CallbackReconciliationState.QUERYING ? 0 : 1),
        rec.nextQueryAt(),
        disposition,
        null,
        null,
        null,
        now);
    // sync outbox summary state lightly
    outboxStore
        .findByOutboxId(rec.outboxId())
        .ifPresent(
            o -> {
              CallbackOutboxState mapped =
                  switch (state) {
                    case CONFIRMED_DELIVERED -> CallbackOutboxState.DELIVERED;
                    case CONFIRMED_REJECTED, EXHAUSTED, EXPIRED -> CallbackOutboxState.DEAD_LETTERED;
                    case CONFIRMED_ABSENT -> CallbackOutboxState.DEAD_LETTERED;
                    case MANUAL_REVIEW, UNKNOWN -> CallbackOutboxState.UNKNOWN;
                    default -> o.state();
                  };
              if (mapped != o.state()
                  && (o.state() == CallbackOutboxState.UNKNOWN
                      || o.state() == CallbackOutboxState.DISPATCHING
                      || o.state() == CallbackOutboxState.RETRY_SCHEDULED
                      || o.state() == CallbackOutboxState.PENDING)) {
                try {
                  outboxStore.updateState(
                      o.outboxId(),
                      o.stateVersion(),
                      mapped,
                      now,
                      o.attemptCount(),
                      disposition != null ? disposition.name() : o.lastErrorCode(),
                      now);
                } catch (RuntimeException ignored) {
                  // optimistic conflict — another worker; ignore
                }
              }
            });
    return Mono.just(outcome);
  }

  private static Duration computeBackoff(int attemptNumber, CallbackReconciliationPolicy policy) {
    double factor = Math.pow(policy.multiplier(), Math.max(0, attemptNumber - 1));
    long millis = (long) (policy.initialBackoff().toMillis() * factor);
    return Duration.ofMillis(Math.max(1, Math.min(millis, policy.maxBackoff().toMillis())));
  }
}
