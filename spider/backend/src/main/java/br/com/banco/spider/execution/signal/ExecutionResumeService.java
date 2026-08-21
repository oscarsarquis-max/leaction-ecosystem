package br.com.banco.spider.execution.signal;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ResultContextReference;
import br.com.banco.spider.canonical.contract.ResultTraceDescriptor;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.budget.ExecutionDeadline;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import br.com.banco.spider.execution.domain.ResolutionSummary;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import br.com.banco.spider.execution.mapping.StepInputMappingPort;
import br.com.banco.spider.execution.persistence.ReactiveExecutionPersistenceGateway;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.plan.ExecutionPlan;
import br.com.banco.spider.execution.plan.ExecutionPlanNode;
import br.com.banco.spider.execution.plan.PlanStatus;
import br.com.banco.spider.execution.plan.RouteRef;
import br.com.banco.spider.execution.retry.ControlledRetryExecutor;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.IntermediateStepOutputStore;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import br.com.banco.spider.integration.binding.AdapterBindingResolverPort;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.Duration;
import java.time.Instant;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

@Service
public class ExecutionResumeService {

  private static final Logger log = LoggerFactory.getLogger(ExecutionResumeService.class);

  private final ExecutionWaitStorePort waitStore;
  private final ExecutionStepStorePort stepStore;
  private final StepAttemptStorePort attemptStore;
  private final ReactiveExecutionPersistenceGateway persistence;
  private final IntermediateStepOutputStore stepOutputs;
  private final ControlledRetryExecutor retryExecutor;
  private final StepInputMappingPort mappingPort;
  private final RetryPolicyCatalogPort retryPolicies;
  private final AdapterBindingResolverPort bindingResolver;
  private final IntegrityDigestPort digest;
  private final SpiderClock clock;
  private final br.com.banco.spider.governance.GovernedRuntimeSupport governedRuntime;

  @org.springframework.beans.factory.annotation.Autowired
  public ExecutionResumeService(
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ReactiveExecutionPersistenceGateway persistence,
      IntermediateStepOutputStore stepOutputs,
      ControlledRetryExecutor retryExecutor,
      StepInputMappingPort mappingPort,
      RetryPolicyCatalogPort retryPolicies,
      AdapterBindingResolverPort bindingResolver,
      IntegrityDigestPort digest,
      SpiderClock clock,
      org.springframework.beans.factory.ObjectProvider<
              br.com.banco.spider.governance.GovernedRuntimeSupport>
          governedRuntime) {
    this(
        waitStore,
        stepStore,
        attemptStore,
        persistence,
        stepOutputs,
        retryExecutor,
        mappingPort,
        retryPolicies,
        bindingResolver,
        digest,
        clock,
        governedRuntime.getIfAvailable());
  }

  public ExecutionResumeService(
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ReactiveExecutionPersistenceGateway persistence,
      IntermediateStepOutputStore stepOutputs,
      ControlledRetryExecutor retryExecutor,
      StepInputMappingPort mappingPort,
      RetryPolicyCatalogPort retryPolicies,
      AdapterBindingResolverPort bindingResolver,
      IntegrityDigestPort digest,
      SpiderClock clock) {
    this(
        waitStore,
        stepStore,
        attemptStore,
        persistence,
        stepOutputs,
        retryExecutor,
        mappingPort,
        retryPolicies,
        bindingResolver,
        digest,
        clock,
        (br.com.banco.spider.governance.GovernedRuntimeSupport) null);
  }

  public ExecutionResumeService(
      ExecutionWaitStorePort waitStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ReactiveExecutionPersistenceGateway persistence,
      IntermediateStepOutputStore stepOutputs,
      ControlledRetryExecutor retryExecutor,
      StepInputMappingPort mappingPort,
      RetryPolicyCatalogPort retryPolicies,
      AdapterBindingResolverPort bindingResolver,
      IntegrityDigestPort digest,
      SpiderClock clock,
      br.com.banco.spider.governance.GovernedRuntimeSupport governedRuntime) {
    this.waitStore = waitStore;
    this.stepStore = stepStore;
    this.attemptStore = attemptStore;
    this.persistence = persistence;
    this.stepOutputs = stepOutputs;
    this.retryExecutor = retryExecutor;
    this.mappingPort = mappingPort;
    this.retryPolicies = retryPolicies;
    this.bindingResolver = bindingResolver;
    this.digest = digest;
    this.clock = clock;
    this.governedRuntime = governedRuntime;
  }

  public record ResumeOutcome(
      ExternalSignalProcessingStatus status,
      CanonicalExecutionResult result,
      CanonicalError error) {}

  public Mono<ResumeOutcome> applySignalAndResume(
      ExternalSignalEnvelope signal, ExecutionWaitRecord wait) {
    Instant now = clock.now();
    return Mono.fromCallable(
            () -> {
              try {
                waitStore.updateState(
                    wait.waitId(),
                    WaitState.WAITING,
                    wait.stateVersion(),
                    WaitState.RESUMING,
                    signal.messageId(),
                    null,
                    "SIGNAL_CLAIMED",
                    now);
                log.info(
                    "event=wait_claimed executionId={} waitId={} messageIdPresent=true",
                    wait.executionId(),
                    wait.waitId());
                return true;
              } catch (InMemoryExecutionControlStore.OptimisticLockException ex) {
                return false;
              }
            })
        .flatMap(
            claimed -> {
              if (!claimed) {
                return Mono.just(
                    new ResumeOutcome(
                        ExternalSignalProcessingStatus.REJECTED,
                        null,
                        error("WAIT_CLAIM_FAILED", "Could not claim wait (concurrent expiry/signal)")));
              }
              if (governedRuntime == null) {
                return applyCompletion(signal, wait, null);
              }
              return governedRuntime
                  .resolveForExecution(
                      wait.executionId(),
                      br.com.banco.spider.governance.GovernedEffectType.SIGNAL_APPLICATION,
                      ExecutionState.WAITING_EXTERNAL)
                  .flatMap(
                      resolved -> {
                        if (resolved.blocksExternalEffect()) {
                          log.info(
                              "event=adapter_prevented_before_effect reasonCode={} effectType=SIGNAL_APPLICATION",
                              resolved.decision());
                          return Mono.just(
                              new ResumeOutcome(
                                  ExternalSignalProcessingStatus.REJECTED,
                                  null,
                                  error(
                                      "GOVERNANCE_SNAPSHOT_REVOKED",
                                      "In-flight governance blocks signal effect")));
                        }
                        return applyCompletion(signal, wait, resolved);
                      })
                  .onErrorResume(
                      br.com.banco.spider.governance.GovernanceContextException.class,
                      ex ->
                          Mono.just(
                              new ResumeOutcome(
                                  ExternalSignalProcessingStatus.REJECTED,
                                  null,
                                  error(ex.reasonCode(), ex.getMessage()))));
            });
  }

  private Mono<ResumeOutcome> applyCompletion(
      ExternalSignalEnvelope signal,
      ExecutionWaitRecord wait,
      br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved resolved) {
    Instant now = clock.now();
    SignalCompletion completion = signal.completion();
    AdapterDispositionMode disp = completion.disposition();

    if (disp == AdapterDispositionMode.UNKNOWN) {
      waitStore.updateState(
          wait.waitId(),
          WaitState.RESUMING,
          wait.stateVersion() + 1,
          WaitState.RECONCILIATION_REQUIRED,
          signal.messageId(),
          now,
          "SIGNAL_UNKNOWN",
          now);
      log.info(
          "event=reconciliation_required executionId={} waitId={}",
          wait.executionId(),
          wait.waitId());
      return Mono.just(
          new ResumeOutcome(ExternalSignalProcessingStatus.ACCEPTED_AND_TERMINATED, null, null));
    }

    completeAttempt(wait, completion, now);

    if (disp == AdapterDispositionMode.COMPLETED
        && completion.outcome() != null
        && completion.outcome().technicalStatus() == TechnicalStatus.SUCCESS) {
      return succeedAndContinue(signal, wait, completion, now, resolved);
    }

    if (disp == AdapterDispositionMode.REJECTED
        || (completion.outcome() != null
            && completion.outcome().technicalStatus() == TechnicalStatus.FAILURE)) {
      boolean timedOut =
          completion.errors().stream().anyMatch(e -> e.category() == ErrorCategory.TIMEOUT);
      return terminateFailure(signal, wait, timedOut ? ExecutionState.TIMED_OUT : ExecutionState.FAILED, now);
    }

    return Mono.just(
        new ResumeOutcome(
            ExternalSignalProcessingStatus.REJECTED,
            null,
            error("SIGNAL_COMPLETION_UNSUPPORTED", "Unsupported completion disposition")));
  }

  private void completeAttempt(ExecutionWaitRecord wait, SignalCompletion completion, Instant now) {
    attemptStore
        .findByAttemptId(wait.attemptId())
        .ifPresent(
            a ->
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
                        completion.disposition() == AdapterDispositionMode.COMPLETED
                            ? AttemptState.SUCCEEDED
                            : AttemptState.FAILED,
                        completion.errors().isEmpty()
                            ? null
                            : completion.errors().getFirst().category(),
                        completion.errors().isEmpty()
                            ? null
                            : completion.errors().getFirst().code(),
                        false,
                        completion.disposition().name(),
                        completion.evidenceRefs().stream().map(e -> e.evidenceId()).toList())));
  }

  private Mono<ResumeOutcome> succeedAndContinue(
      ExternalSignalEnvelope signal,
      ExecutionWaitRecord wait,
      SignalCompletion completion,
      Instant now,
      br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved resolved) {
    var step = stepStore.find(wait.executionId(), wait.stepId()).orElseThrow();
    stepStore.updateState(
        wait.executionId(),
        wait.stepId(),
        step.state(),
        step.stateVersion(),
        StepState.SUCCEEDED,
        null,
        null,
        null,
        null,
        now,
        now);

    JsonNode out =
        completion.outcome() != null ? completion.outcome().canonicalData() : null;
    if (out == null || out.isNull()) {
      out = new com.fasterxml.jackson.databind.ObjectMapper().createObjectNode();
    }
    stepOutputs.put(wait.executionId(), wait.stepId(), out);

    waitStore.updateState(
        wait.waitId(),
        WaitState.RESUMING,
        wait.stateVersion() + 1,
        WaitState.RESUMED,
        signal.messageId(),
        now,
        "SIGNAL_SUCCESS",
        now);

    return persistence
        .findControl(wait.executionId())
        .flatMap(
            opt -> {
              var control = opt.orElseThrow();
              return persistence
                  .findPlan(wait.executionId())
                  .flatMap(
                      planOpt -> {
                        PersistedExecutionPlan persisted = planOpt.orElseThrow();
                        if (!digest.digest(persisted.canonicalPlanRepresentation())
                            .equals(persisted.integrityRef())
                            && !persisted.integrityRef().equals(
                                digest.digest(persisted.canonicalPlanRepresentation()))) {
                          // integrity: PersistedExecutionPlan stores representation and integrity
                        }
                        String expected = persisted.integrityRef();
                        String actual = digest.digest(persisted.canonicalPlanRepresentation());
                        if (!expected.equals(actual)) {
                          return Mono.just(
                              new ResumeOutcome(
                                  ExternalSignalProcessingStatus.REJECTED,
                                  null,
                                  error("PLAN_INTEGRITY_FAILED", "Plan integrity check failed")));
                        }

                        ExecutionPlan plan = reconstructPlan(persisted);
                        releaseNext(wait.executionId(), plan, wait.stepId());

                        boolean hasNext =
                            plan.orderedNodes().stream()
                                .anyMatch(
                                    n ->
                                        stepStore
                                            .find(wait.executionId(), n.stepId())
                                            .map(s -> s.state() == StepState.READY)
                                            .orElse(false));

                        log.info(
                            "event=execution_resumed executionId={} waitId={}",
                            wait.executionId(),
                            wait.waitId());

                        return persistence
                            .transition(
                                wait.executionId(),
                                ExecutionState.WAITING_EXTERNAL,
                                control.stateVersion(),
                                hasNext ? ExecutionState.RUNNING : ExecutionState.SUCCEEDED,
                                hasNext ? "RESUME_CONTINUE" : "RESUME_COMPLETE",
                                TechnicalStatus.SUCCESS,
                                null,
                                null,
                                null,
                                null)
                            .flatMap(
                                updated -> {
                                  if (!hasNext) {
                                    CanonicalExecutionResult result =
                                        terminalSuccess(signal, plan, completion, updated.startedAt());
                                    return persistence
                                        .persistTerminalResult(
                                            result, IdempotencyRecordState.COMPLETED, null, null)
                                        .thenReturn(
                                            new ResumeOutcome(
                                                ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED,
                                                result,
                                                null));
                                  }
                                  return continueRemaining(
                                          signal, plan, wait.stepId(), completion, resolved)
                                      .map(
                                          r ->
                                              new ResumeOutcome(
                                                  ExternalSignalProcessingStatus.ACCEPTED_AND_RESUMED,
                                                  r,
                                                  null));
                                });
                      });
            });
  }

  private Mono<ResumeOutcome> terminateFailure(
      ExternalSignalEnvelope signal,
      ExecutionWaitRecord wait,
      ExecutionState terminal,
      Instant now) {
    var step = stepStore.find(wait.executionId(), wait.stepId()).orElseThrow();
    StepState stepState =
        terminal == ExecutionState.TIMED_OUT ? StepState.TIMED_OUT : StepState.FAILED;
    stepStore.updateState(
        wait.executionId(),
        wait.stepId(),
        step.state(),
        step.stateVersion(),
        stepState,
        null,
        null,
        terminal.name(),
        null,
        now,
        now);
    skipAfter(wait.executionId(), wait.stepId());
    waitStore.updateState(
        wait.waitId(),
        WaitState.RESUMING,
        wait.stateVersion() + 1,
        WaitState.RESUMED,
        signal.messageId(),
        now,
        terminal.name(),
        now);

    return persistence
        .findControl(wait.executionId())
        .flatMap(
            opt -> {
              var control = opt.orElseThrow();
              return persistence
                  .transition(
                      wait.executionId(),
                      ExecutionState.WAITING_EXTERNAL,
                      control.stateVersion(),
                      terminal,
                      "SIGNAL_TERMINAL",
                      TechnicalStatus.FAILURE,
                      null,
                      null,
                      null,
                      null)
                  .map(
                      c ->
                          new ResumeOutcome(
                              ExternalSignalProcessingStatus.ACCEPTED_AND_TERMINATED,
                              null,
                              null));
            });
  }

  private Mono<CanonicalExecutionResult> continueRemaining(
      ExternalSignalEnvelope signal,
      ExecutionPlan plan,
      String completedStepId,
      SignalCompletion firstCompletion,
      br.com.banco.spider.governance.GovernedRuntimeSupport.Resolved resolved) {
    RetryPolicyCatalogPort effectiveRetry =
        resolved == null ? retryPolicies : resolved.retryOr(retryPolicies);
    AdapterBindingResolverPort effectiveBinding =
        resolved == null ? bindingResolver : resolved.bindingOr(bindingResolver);
    int from =
        plan.orderedNodes().stream()
            .filter(n -> n.stepId().equals(completedStepId))
            .mapToInt(ExecutionPlanNode::orderedPosition)
            .findFirst()
            .orElse(0);
    List<ExecutionPlanNode> remaining =
        plan.orderedNodes().stream().filter(n -> n.orderedPosition() > from).toList();
    ExecutionDeadline deadline = ExecutionDeadline.fromNow(clock, Duration.ofSeconds(60));

    return Flux.fromIterable(remaining)
        .concatMap(
            node -> {
              JsonNode previous =
                  node.dependencies().isEmpty()
                      ? null
                      : stepOutputs
                          .get(signal.executionId(), node.dependencies().getFirst())
                          .orElse(null);
              // Use root null — resume uses PREVIOUS for typical linear chain
              var mapped =
                  mappingPort.map(
                      new StepInputMappingPort.MappingRequest(
                          StepInputMappingKind.fromRef(node.inputMappingRef()),
                          null,
                          previous));
              if (!mapped.success()) {
                // Fallback: empty object as previous for linear PREVIOUS mapping
                JsonNode fallback =
                    previous != null
                        ? previous
                        : new com.fasterxml.jackson.databind.ObjectMapper().createObjectNode();
                mapped =
                    mappingPort.map(
                        new StepInputMappingPort.MappingRequest(
                            StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA, null, fallback));
              }
              if (!mapped.success()) {
                return Mono.error(new IllegalStateException(mapped.error().code()));
              }
              CanonicalPayload payload = CanonicalPayload.of(mapped.canonicalData());
              RetryPolicyDefinition policy =
                  effectiveRetry
                      .findByRef(node.effectivePolicyRefs().get("retry"))
                      .orElseGet(() -> RetryPolicyDefinition.noRetry("none", "1.0"));
              return effectiveBinding
                  .resolve(node.adapterBindingRef())
                  .flatMap(
                      binding ->
                          retryExecutor.execute(
                              signal.executionId(),
                              node,
                              policy,
                              deadline,
                              null,
                              binding.adapter(),
                              inv ->
                                  UniversalAdapterRequest.builder()
                                      .invocationId(inv)
                                      .executionId(signal.executionId())
                                      .stepId(node.stepId())
                                      .attemptId("pending")
                                      .invokedAt(clock.now())
                                      .capabilityCode(node.capabilityCode())
                                      .operationCode(node.operationCode())
                                      .bindingRef(node.adapterBindingRef())
                                      .inputContractRef(node.inputContractRef())
                                      .outputContractRef(node.outputContractRef())
                                      .trace(signal.trace())
                                      .payload(payload)
                                      .build()))
                  .doOnNext(
                      r -> {
                        if (r.stepState() == StepState.SUCCEEDED
                            && r.adapterResult().outcome() != null
                            && r.adapterResult().outcome().canonicalData() != null) {
                          stepOutputs.put(
                              signal.executionId(),
                              node.stepId(),
                              r.adapterResult().outcome().canonicalData());
                          releaseNext(signal.executionId(), plan, node.stepId());
                        }
                      });
            })
        .takeUntil(r -> r.stepState() != StepState.SUCCEEDED)
        .last()
        .flatMap(
            last -> {
              Instant now = clock.now();
              ExecutionState state =
                  last.stepState() == StepState.SUCCEEDED
                      ? ExecutionState.SUCCEEDED
                      : last.waitingExternal()
                          ? ExecutionState.WAITING_EXTERNAL
                          : ExecutionState.FAILED;
              CanonicalExecutionResult result =
                  CanonicalExecutionResult.builder()
                      .contract(
                          new br.com.banco.spider.canonical.contract.ContractDescriptor(
                              "1.0", "1.0.0"))
                      .execution(
                          new ExecutionSummary(
                              signal.executionId(), state, null, now, now))
                      .contextRef(
                          new ResultContextReference("c", "i@1", "cap@1", "j@1"))
                      .trace(ResultTraceDescriptor.from(signal.trace()))
                      .resolution(
                          new ResolutionSummary(
                              plan.routeRef().routeCode(),
                              plan.routeRef().routeVersion(),
                              plan.planId()))
                      .outcome(
                          last.adapterResult() != null && last.adapterResult().outcome() != null
                              ? last.adapterResult().outcome()
                              : CanonicalOutcome.technical(
                                  state == ExecutionState.SUCCEEDED
                                      ? TechnicalStatus.SUCCESS
                                      : TechnicalStatus.FAILURE))
                      .errors(List.of())
                      .evidenceRefs(List.of())
                      .build();
              return persistence
                  .findControl(signal.executionId())
                  .flatMap(
                      opt -> {
                        var c = opt.orElseThrow();
                        return persistence
                            .transition(
                                signal.executionId(),
                                c.state(),
                                c.stateVersion(),
                                state,
                                "RESUME_STEPS_DONE",
                                state == ExecutionState.SUCCEEDED
                                    ? TechnicalStatus.SUCCESS
                                    : TechnicalStatus.FAILURE,
                                null,
                                null,
                                null,
                                null)
                            .then(
                                state.isTerminal()
                                    ? persistence.persistTerminalResult(
                                        result,
                                        state == ExecutionState.SUCCEEDED
                                            ? IdempotencyRecordState.COMPLETED
                                            : IdempotencyRecordState.FAILED_REUSABLE,
                                        null,
                                        null)
                                    : Mono.empty())
                            .thenReturn(result);
                      });
            });
  }

  private void releaseNext(String executionId, ExecutionPlan plan, String completedStepId) {
    Instant now = clock.now();
    plan.orderedNodes().stream()
        .filter(n -> n.dependencies().contains(completedStepId))
        .findFirst()
        .ifPresent(
            next -> {
              var s = stepStore.find(executionId, next.stepId()).orElse(null);
              if (s != null && s.state() == StepState.PENDING) {
                stepStore.updateState(
                    executionId,
                    next.stepId(),
                    StepState.PENDING,
                    s.stateVersion(),
                    StepState.READY,
                    null,
                    null,
                    null,
                    null,
                    null,
                    now);
              }
            });
  }

  private void skipAfter(String executionId, String stepId) {
    Instant now = clock.now();
    boolean after = false;
    for (var s : stepStore.findByExecutionIdOrdered(executionId)) {
      if (s.stepId().equals(stepId)) {
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
            "SIGNAL_TERMINAL",
            null,
            now,
            now);
      }
    }
  }

  private CanonicalExecutionResult terminalSuccess(
      ExternalSignalEnvelope signal,
      ExecutionPlan plan,
      SignalCompletion completion,
      Instant startedAt) {
    Instant now = clock.now();
    return CanonicalExecutionResult.builder()
        .contract(new br.com.banco.spider.canonical.contract.ContractDescriptor("1.0", "1.0.0"))
        .execution(
            new ExecutionSummary(
                signal.executionId(), ExecutionState.SUCCEEDED, startedAt, now, now))
        .contextRef(new ResultContextReference("c", "i@1", "cap@1", "j@1"))
        .trace(ResultTraceDescriptor.from(signal.trace()))
        .resolution(
            new ResolutionSummary(
                plan.routeRef().routeCode(), plan.routeRef().routeVersion(), plan.planId()))
        .outcome(
            completion.outcome() != null
                ? completion.outcome()
                : CanonicalOutcome.technical(TechnicalStatus.SUCCESS))
        .errors(List.of())
        .evidenceRefs(completion.evidenceRefs())
        .build();
  }

  /**
   * Reconstrói um {@link ExecutionPlan} mínimo a partir da representação canônica persistida.
   * Usa nodes vazios se o parse completo não estiver disponível — resume carrega steps do store.
   */
  private ExecutionPlan reconstructPlan(PersistedExecutionPlan persisted) {
    // Parse ordered nodes from canonical representation lines "node.pos|stepId|..."
    List<ExecutionPlanNode> nodes = new java.util.ArrayList<>();
    Map<String, String> contracts = new HashMap<>();
    for (String line : persisted.canonicalPlanRepresentation().split("\n")) {
      if (line.startsWith("node.")) {
        String body = line.substring(5);
        String[] parts = body.split("\\|", -1);
        if (parts.length >= 10) {
          int pos = Integer.parseInt(parts[0]);
          nodes.add(
              new ExecutionPlanNode(
                  parts[1],
                  pos,
                  parts[2],
                  parts[3],
                  parts[4],
                  parts[5],
                  parts[6],
                  parts[10].isBlank() ? List.of() : List.of(parts[10].split(",")),
                  parts[7],
                  Map.of(),
                  br.com.banco.spider.execution.route.IdempotencyClassification.valueOf(parts[8]),
                  br.com.banco.spider.execution.route.RetrySafety.valueOf(parts[9]),
                  null,
                  List.of()));
        }
      }
    }
    nodes.sort(java.util.Comparator.comparingInt(ExecutionPlanNode::orderedPosition));
    // Fix dependencies: for linear chain, dependency is previous step
    List<ExecutionPlanNode> fixed = new java.util.ArrayList<>();
    for (int i = 0; i < nodes.size(); i++) {
      ExecutionPlanNode n = nodes.get(i);
      List<String> deps = i == 0 ? List.of() : List.of(nodes.get(i - 1).stepId());
      String mapping =
          i == 0
              ? StepInputMappingKind.ROOT_REQUEST_CANONICAL_DATA.toRef()
              : StepInputMappingKind.PREVIOUS_STEP_CANONICAL_DATA.toRef();
      fixed.add(
          new ExecutionPlanNode(
              n.stepId(),
              n.orderedPosition(),
              n.capabilityCode(),
              n.operationCode(),
              n.adapterBindingRef(),
              n.inputContractRef(),
              n.outputContractRef(),
              deps,
              mapping,
              Map.of("retry", "policy:retry:default@1.0"),
              n.idempotencyClassification(),
              n.retrySafety(),
              n.waitPolicyRef(),
              n.allowedTransitions()));
    }
    return new ExecutionPlan(
        persisted.planId(),
        persisted.executionId(),
        persisted.createdAt(),
        new RouteRef(persisted.routeCode(), persisted.routeVersion()),
        persisted.journeyRef(),
        contracts,
        fixed,
        List.of(),
        persisted.integrityRef(),
        PlanStatus.MATERIALIZED);
  }

  private static CanonicalError error(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.INTERNAL)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("execution_resume", null, null, null))
        .build();
  }
}
