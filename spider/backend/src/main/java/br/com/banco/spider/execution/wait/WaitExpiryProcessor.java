package br.com.banco.spider.execution.wait;

import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.ReactiveExecutionPersistenceGateway;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.governance.GovernedEffectType;
import br.com.banco.spider.governance.GovernedRuntimeSupport;
import br.com.banco.spider.governance.GovernanceInFlightDecision;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class WaitExpiryProcessor {

  private static final Logger log = LoggerFactory.getLogger(WaitExpiryProcessor.class);

  private final ExecutionWaitStorePort waitStore;
  private final ExecutionStepStorePort stepStore;
  private final StepAttemptStorePort attemptStore;
  private final ReactiveExecutionPersistenceGateway persistence;
  private final WaitPolicyCatalogPort catalog;
  private final SpiderClock clock;
  private final GovernedRuntimeSupport governedRuntime;

  @org.springframework.beans.factory.annotation.Autowired
  public WaitExpiryProcessor(
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ReactiveExecutionPersistenceGateway persistence,
      WaitPolicyCatalogPort catalog,
      SpiderClock clock,
      ObjectProvider<GovernedRuntimeSupport> governedRuntime) {
    this(
        waitStore,
        stepStore,
        attemptStore,
        persistence,
        catalog,
        clock,
        governedRuntime.getIfAvailable());
  }

  public WaitExpiryProcessor(
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ReactiveExecutionPersistenceGateway persistence,
      WaitPolicyCatalogPort catalog,
      SpiderClock clock) {
    this(waitStore, stepStore, attemptStore, persistence, catalog, clock, (GovernedRuntimeSupport) null);
  }

  public WaitExpiryProcessor(
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ReactiveExecutionPersistenceGateway persistence,
      WaitPolicyCatalogPort catalog,
      SpiderClock clock,
      GovernedRuntimeSupport governedRuntime) {
    this.waitStore = waitStore;
    this.stepStore = stepStore;
    this.attemptStore = attemptStore;
    this.persistence = persistence;
    this.catalog = catalog;
    this.clock = clock;
    this.governedRuntime = governedRuntime;
  }

  public List<ExecutionWaitRecord> findExpiredWaiting() {
    return waitStore.findExpiredWaiting(clock.now());
  }

  public Mono<Boolean> expire(String waitId, long expectedVersion) {
    Instant now = clock.now();
    return Mono.fromCallable(
            () ->
                waitStore
                    .findByWaitId(waitId)
                    .orElseThrow(() -> new IllegalStateException("Wait not found")))
        .flatMap(
            wait -> {
              if (wait.state() != WaitState.WAITING || wait.stateVersion() != expectedVersion) {
                return Mono.just(false);
              }
              Mono<GovernedRuntimeSupport.Resolved> resolvedMono =
                  governedRuntime == null
                      ? Mono.just(
                          new GovernedRuntimeSupport.Resolved(
                              Optional.empty(),
                              Optional.empty(),
                              GovernanceInFlightDecision.ALLOW_FIXED_SNAPSHOT))
                      : governedRuntime.resolveForExecution(
                          wait.executionId(),
                          GovernedEffectType.WAIT_EXPIRY_EXTERNAL_EFFECT,
                          ExecutionState.WAITING_EXTERNAL);
              return resolvedMono.flatMap(
                  resolved -> {
                    if (resolved.blocksExternalEffect()) {
                      log.info(
                          "event=adapter_prevented_before_effect reasonCode={} effectType=WAIT_EXPIRY",
                          resolved.decision());
                      return Mono.just(false);
                    }
                    WaitPolicyCatalogPort effective = resolved.waitOr(catalog);
                    return expireClaimed(wait, expectedVersion, now, effective);
                  });
            });
  }

  private Mono<Boolean> expireClaimed(
      ExecutionWaitRecord wait,
      long expectedVersion,
      Instant now,
      WaitPolicyCatalogPort effectiveCatalog) {
    WaitPolicyDefinition policy =
        effectiveCatalog.findByRef(wait.waitPolicyRef()).orElse(null);
    WaitExpiryAction action =
        policy != null ? policy.expiryAction() : WaitExpiryAction.TIME_OUT_EXECUTION;

    try {
      waitStore.updateState(
          wait.waitId(),
          WaitState.WAITING,
          expectedVersion,
          WaitState.EXPIRING,
          null,
          null,
          "EXPIRING",
          now);
    } catch (InMemoryExecutionControlStore.OptimisticLockException ex) {
      log.info("event=wait_expired waitId={} reasonCode=LOST_RACE_TO_SIGNAL", wait.waitId());
      return Mono.just(false);
    }

    WaitState terminalWait =
        action == WaitExpiryAction.OPEN_RECONCILIATION
            ? WaitState.RECONCILIATION_REQUIRED
            : WaitState.EXPIRED;
    waitStore.updateState(
        wait.waitId(),
        WaitState.EXPIRING,
        expectedVersion + 1,
        terminalWait,
        null,
        now,
        action.name(),
        now);

    var step = stepStore.find(wait.executionId(), wait.stepId()).orElseThrow();
    StepState stepState =
        action == WaitExpiryAction.FAIL_EXECUTION
            ? StepState.FAILED
            : action == WaitExpiryAction.OPEN_RECONCILIATION
                ? StepState.WAITING_EXTERNAL
                : StepState.TIMED_OUT;
    if (step.state() == StepState.WAITING_EXTERNAL) {
      stepStore.updateState(
          wait.executionId(),
          wait.stepId(),
          StepState.WAITING_EXTERNAL,
          step.stateVersion(),
          stepState,
          null,
          null,
          action.name(),
          null,
          now,
          now);
    }

    attemptStore
        .findByAttemptId(wait.attemptId())
        .ifPresent(
            a -> {
              if (a.state() == AttemptState.WAITING_EXTERNAL || a.state() == AttemptState.UNKNOWN) {
                attemptStore.update(
                    new StepAttemptRecord(
                        a.attemptId(),
                        a.executionId(),
                        a.stepId(),
                        a.attemptNumber(),
                        a.invocationId(),
                        a.adapterBindingRef(),
                        a.startedAt(),
                        a.deadline(),
                        now,
                        AttemptState.TIMED_OUT,
                        ErrorCategory.TIMEOUT,
                        "WAIT_EXPIRED",
                        false,
                        action.name(),
                        a.evidenceRefs()));
              }
            });

    skipPending(wait.executionId(), wait.stepId());
    log.info(
        "event=wait_expired executionId={} waitId={} action={} usingFixedPolicy=true",
        wait.executionId(),
        wait.waitId(),
        action);

    if (action == WaitExpiryAction.OPEN_RECONCILIATION) {
      return Mono.just(true);
    }

    return persistence
        .findControl(wait.executionId())
        .flatMap(
            opt -> {
              var control = opt.orElseThrow();
              if (control.state() != ExecutionState.WAITING_EXTERNAL) {
                return Mono.just(true);
              }
              ExecutionState target =
                  action == WaitExpiryAction.FAIL_EXECUTION
                      ? ExecutionState.FAILED
                      : ExecutionState.TIMED_OUT;
              return persistence
                  .transition(
                      control.executionId(),
                      ExecutionState.WAITING_EXTERNAL,
                      control.stateVersion(),
                      target,
                      "WAIT_EXPIRED",
                      TechnicalStatus.FAILURE,
                      null,
                      null,
                      null,
                      null)
                  .thenReturn(true);
            });
  }

  private void skipPending(String executionId, String failedStepId) {
    Instant now = clock.now();
    var steps = stepStore.findByExecutionIdOrdered(executionId);
    boolean after = false;
    for (var s : steps) {
      if (s.stepId().equals(failedStepId)) {
        after = true;
        continue;
      }
      if (after && (s.state() == StepState.PENDING || s.state() == StepState.READY)) {
        stepStore.updateState(
            executionId,
            s.stepId(),
            s.state(),
            s.stateVersion(),
            StepState.SKIPPED,
            null,
            null,
            "WAIT_EXPIRED",
            null,
            now,
            now);
      }
    }
  }
}
