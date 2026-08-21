package br.com.banco.spider.execution.retry;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.execution.budget.ExecutionDeadline;
import br.com.banco.spider.execution.budget.RetryBudgetCalculator;
import br.com.banco.spider.execution.budget.StepExecutionBudget;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.engine.AdapterResultMapper;
import br.com.banco.spider.execution.plan.ExecutionPlanNode;
import br.com.banco.spider.execution.route.RetrySafety;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import br.com.banco.spider.integration.port.UniversalAdapterResult;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import java.time.Duration;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/**
 * Retry técnico explícito e reativo — uma invocação Adapter por attempt, com persistência.
 * Sem jitter neste incremento.
 */
@Component
public class ControlledRetryExecutor {

  private static final Logger log = LoggerFactory.getLogger(ControlledRetryExecutor.class);

  private static final Set<ErrorCategory> NEVER_RETRY =
      EnumSet.of(
          ErrorCategory.AUTHENTICATION,
          ErrorCategory.AUTHORIZATION,
          ErrorCategory.VALIDATION,
          ErrorCategory.IDEMPOTENCY,
          ErrorCategory.BUSINESS_OUTCOME);

  private final ExecutionStepStorePort stepStore;
  private final StepAttemptStorePort attemptStore;
  private final BackoffStrategyPort backoff;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public ControlledRetryExecutor(
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      BackoffStrategyPort backoff,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.stepStore = stepStore;
    this.attemptStore = attemptStore;
    this.backoff = backoff;
    this.ids = ids;
    this.clock = clock;
  }

  public record StepInvokeResult(
      UniversalAdapterResult adapterResult,
      AdapterResultMapper.MappedTerminal mapped,
      StepState stepState,
      int attemptsUsed,
      boolean waitingExternal) {}

  @FunctionalInterface
  public interface AdapterInvocation {
    Mono<UniversalAdapterResult> invoke(UniversalAdapterRequest request);
  }

  public Mono<StepInvokeResult> execute(
      String executionId,
      ExecutionPlanNode node,
      RetryPolicyDefinition policy,
      ExecutionDeadline executionDeadline,
      String idempotencyKeyForAdapter,
      UniversalAdapterPort adapter,
      java.util.function.Function<String, UniversalAdapterRequest> requestFactory) {

    RetryPolicyDefinition effective =
        policy != null ? policy : RetryPolicyDefinition.noRetry("none", "1.0");

    return executeAttempt(executionId, node, effective, executionDeadline, idempotencyKeyForAdapter, adapter, requestFactory, 0);
  }

  private Mono<StepInvokeResult> executeAttempt(
      String executionId,
      ExecutionPlanNode node,
      RetryPolicyDefinition policy,
      ExecutionDeadline executionDeadline,
      String idempotencyKey,
      UniversalAdapterPort adapter,
      java.util.function.Function<String, UniversalAdapterRequest> requestFactory,
      int completedAttempts) {

    if (executionDeadline.isExpired(clock)) {
      return Mono.just(timeoutResult(null, completedAttempts));
    }

    StepExecutionBudget budget =
        RetryBudgetCalculator.forStep(executionDeadline, clock, Duration.ofSeconds(30));
    if (!budget.hasUsefulBudget(clock, Duration.ofMillis(1))) {
      log.info(
          "event=retry_budget_exhausted executionId={} stepId={} reasonCode=NO_USEFUL_BUDGET",
          executionId,
          node.stepId());
      return Mono.just(timeoutResult(null, completedAttempts));
    }

    Instant now = clock.now();
    int attemptNumber = attemptStore.nextAttemptNumber(executionId, node.stepId());
    String attemptId = ids.nextId("att");
    String invocationId = ids.nextId("inv");

    var step =
        stepStore
            .find(executionId, node.stepId())
            .orElseThrow(() -> new IllegalStateException("Step missing " + node.stepId()));

    // First attempt: READY -> RUNNING; retry keeps RUNNING after failed non-terminal
    if (step.state() == StepState.READY) {
      stepStore.updateState(
          executionId,
          node.stepId(),
          StepState.READY,
          step.stateVersion(),
          StepState.RUNNING,
          attemptId,
          null,
          null,
          now,
          null,
          now);
      log.info("event=step_running executionId={} stepId={}", executionId, node.stepId());
    } else if (step.state() == StepState.RUNNING) {
      stepStore.updateState(
          executionId,
          node.stepId(),
          StepState.RUNNING,
          step.stateVersion(),
          StepState.RUNNING,
          attemptId,
          null,
          null,
          null,
          null,
          now);
    }

    StepAttemptRecord started =
        new StepAttemptRecord(
            attemptId,
            executionId,
            node.stepId(),
            attemptNumber,
            invocationId,
            node.adapterBindingRef(),
            now,
            budget.stepDeadline(),
            null,
            AttemptState.STARTED,
            null,
            null,
            null,
            null,
            List.of());
    attemptStore.insert(started);
    log.info(
        "event=attempt_started executionId={} stepId={} attemptNumber={} attemptId={}",
        executionId,
        node.stepId(),
        attemptNumber,
        attemptId);

    UniversalAdapterRequest adapterRequest = requestFactory.apply(invocationId);
    // Override attempt/invocation/deadline/idempotency if factory didn't set
    adapterRequest =
        UniversalAdapterRequest.builder()
            .invocationId(invocationId)
            .executionId(executionId)
            .stepId(node.stepId())
            .attemptId(attemptId)
            .invokedAt(now)
            .capabilityCode(node.capabilityCode())
            .operationCode(node.operationCode())
            .bindingRef(node.adapterBindingRef())
            .inputContractRef(node.inputContractRef())
            .outputContractRef(node.outputContractRef())
            .trace(adapterRequest.trace())
            .deadline(budget.stepDeadline())
            .idempotencyKey(idempotencyKey)
            .payload(adapterRequest.payload())
            .build();

    return adapter
        .invoke(adapterRequest)
        .flatMap(
            result -> {
              AdapterResultMapper.MappedTerminal mapped = AdapterResultMapper.map(result);
              Instant completed = clock.now();
              AttemptState attemptState = toAttemptState(mapped, result);
              List<String> evidence =
                  result.evidenceRefs() == null
                      ? List.of()
                      : result.evidenceRefs().stream().map(e -> e.evidenceId()).toList();

              CanonicalError firstError =
                  result.errors() == null || result.errors().isEmpty()
                      ? null
                      : result.errors().getFirst();

              StepAttemptRecord finished =
                  new StepAttemptRecord(
                      attemptId,
                      executionId,
                      node.stepId(),
                      attemptNumber,
                      invocationId,
                      node.adapterBindingRef(),
                      now,
                      budget.stepDeadline(),
                      completed,
                      attemptState,
                      firstError != null ? firstError.category() : null,
                      firstError != null ? firstError.code() : null,
                      firstError != null ? firstError.retryable() : null,
                      result.dispositionMode().name(),
                      evidence);
              attemptStore.update(finished);
              log.info(
                  "event=attempt_completed executionId={} stepId={} attemptNumber={} disposition={}",
                  executionId,
                  node.stepId(),
                  attemptNumber,
                  result.dispositionMode());

              int used = completedAttempts + 1;

              if (result.dispositionMode() == AdapterDispositionMode.ACCEPTED_ASYNC
                  || result.dispositionMode() == AdapterDispositionMode.UNKNOWN) {
                markStep(executionId, node.stepId(), StepState.WAITING_EXTERNAL, null, null);
                log.info(
                    "event=route_stopped executionId={} stepId={} reasonCode=WAITING_EXTERNAL",
                    executionId,
                    node.stepId());
                return Mono.just(
                    new StepInvokeResult(result, mapped, StepState.WAITING_EXTERNAL, used, true));
              }

              if (mapped.state().name().equals("SUCCEEDED")) {
                markStep(executionId, node.stepId(), StepState.SUCCEEDED, null, null);
                log.info(
                    "event=step_terminal executionId={} stepId={} state=SUCCEEDED",
                    executionId,
                    node.stepId());
                return Mono.just(
                    new StepInvokeResult(result, mapped, StepState.SUCCEEDED, used, false));
              }

              // Failure / timeout path — evaluate retry
              boolean allowRetry =
                  shouldRetry(node, policy, result, firstError, used, executionDeadline);
              if (allowRetry) {
                Duration wait = backoff.nextBackoff(policy, used);
                if (!RetryBudgetCalculator.canScheduleBackoff(executionDeadline, clock, wait)) {
                  log.info(
                      "event=retry_suppressed executionId={} stepId={} reasonCode=BUDGET",
                      executionId,
                      node.stepId());
                  StepState terminal =
                      mapped.state().name().equals("TIMED_OUT")
                          ? StepState.TIMED_OUT
                          : StepState.FAILED;
                  markStep(
                      executionId,
                      node.stepId(),
                      terminal,
                      firstError != null ? firstError.code() : "RETRY_BUDGET",
                      null);
                  return Mono.just(new StepInvokeResult(result, mapped, terminal, used, false));
                }
                log.info(
                    "event=retry_scheduled executionId={} stepId={} attempt={} backoffMs={}",
                    executionId,
                    node.stepId(),
                    used,
                    wait.toMillis());
                // Zero-delay in tests when backoff is tiny; still explicit chain
                return Mono.delay(wait.isZero() ? Duration.ofMillis(1) : wait)
                    .then(
                        executeAttempt(
                            executionId,
                            node,
                            policy,
                            executionDeadline,
                            idempotencyKey,
                            adapter,
                            requestFactory,
                            used));
              }

              StepState terminal =
                  mapped.state().name().equals("TIMED_OUT") ? StepState.TIMED_OUT : StepState.FAILED;
              markStep(
                  executionId,
                  node.stepId(),
                  terminal,
                  firstError != null ? firstError.code() : mapped.state().name(),
                  null);
              log.info(
                  "event=step_terminal executionId={} stepId={} state={} reasonCode=RETRY_EXHAUSTED_OR_FORBIDDEN",
                  executionId,
                  node.stepId(),
                  terminal);
              return Mono.just(new StepInvokeResult(result, mapped, terminal, used, false));
            });
  }

  private boolean shouldRetry(
      ExecutionPlanNode node,
      RetryPolicyDefinition policy,
      UniversalAdapterResult result,
      CanonicalError firstError,
      int usedAttempts,
      ExecutionDeadline deadline) {
    if (usedAttempts >= policy.maxAttempts()) {
      return false;
    }
    if (node.retrySafety() == RetrySafety.UNSAFE) {
      log.info(
          "event=retry_suppressed stepId={} reasonCode=UNSAFE", node.stepId());
      return false;
    }
    if (result.dispositionMode() == AdapterDispositionMode.ACCEPTED_ASYNC
        || result.dispositionMode() == AdapterDispositionMode.UNKNOWN) {
      return false;
    }
    if (result.dispositionMode() == AdapterDispositionMode.COMPLETED
        && result.outcome() != null
        && result.outcome().technicalStatus() == TechnicalStatus.SUCCESS) {
      return false; // business negative stays success — no retry
    }
    if (firstError == null) {
      return false;
    }
    if (!firstError.retryable()) {
      return false;
    }
    if (NEVER_RETRY.contains(firstError.category())) {
      return false;
    }
    if (policy.retryableCategories().isEmpty() && policy.retryableCodes().isEmpty()) {
      return false;
    }
    boolean catOk =
        policy.retryableCategories().isEmpty()
            || policy.retryableCategories().contains(firstError.category());
    boolean codeOk =
        policy.retryableCodes().isEmpty() || policy.retryableCodes().contains(firstError.code());
    if (!(catOk && codeOk)) {
      return false;
    }
    if (node.retrySafety() == RetrySafety.SAFE_WITH_IDEMPOTENCY_KEY) {
      // key checked by caller before invoke; if we got here key was present
      return true;
    }
    return node.retrySafety() == RetrySafety.SAFE;
  }

  private void markStep(
      String executionId, String stepId, StepState newState, String errorCode, String outputRef) {
    var step = stepStore.find(executionId, stepId).orElseThrow();
    Instant now = clock.now();
    stepStore.updateState(
        executionId,
        stepId,
        step.state(),
        step.stateVersion(),
        newState,
        null,
        outputRef,
        errorCode,
        null,
        newState.isTerminal() || newState == StepState.WAITING_EXTERNAL ? now : null,
        now);
  }

  private static AttemptState toAttemptState(
      AdapterResultMapper.MappedTerminal mapped, UniversalAdapterResult result) {
    return switch (result.dispositionMode()) {
      case COMPLETED ->
          mapped.state().name().equals("SUCCEEDED") ? AttemptState.SUCCEEDED : AttemptState.FAILED;
      case ACCEPTED_ASYNC -> AttemptState.WAITING_EXTERNAL;
      case UNKNOWN -> AttemptState.UNKNOWN;
      case REJECTED ->
          mapped.state().name().equals("TIMED_OUT") ? AttemptState.TIMED_OUT : AttemptState.FAILED;
    };
  }

  private StepInvokeResult timeoutResult(UniversalAdapterResult result, int used) {
    return new StepInvokeResult(
        result,
        new AdapterResultMapper.MappedTerminal(
            br.com.banco.spider.execution.domain.ExecutionState.TIMED_OUT,
            TechnicalStatus.FAILURE),
        StepState.TIMED_OUT,
        used,
        false);
  }
}
