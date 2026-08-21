package br.com.banco.spider.execution.engine;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ResultContextReference;
import br.com.banco.spider.canonical.contract.ResultTraceDescriptor;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.canonical.validation.OperationClass;
import br.com.banco.spider.canonical.validation.ValidationOutcome;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import br.com.banco.spider.execution.budget.ExecutionDeadline;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.ExecutionSummary;
import br.com.banco.spider.execution.domain.ResolutionSummary;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.fingerprint.IdempotencyKeyHashPort;
import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import br.com.banco.spider.execution.mapping.StepInputMappingPort;
import br.com.banco.spider.execution.persistence.ReactiveExecutionPersistenceGateway;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyReservationResult;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyReservationStatus;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyScope;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.plan.ExecutionPlan;
import br.com.banco.spider.execution.plan.ExecutionPlanMaterialization;
import br.com.banco.spider.execution.plan.ExecutionPlanMaterializerPort;
import br.com.banco.spider.execution.plan.ExecutionPlanNode;
import br.com.banco.spider.execution.port.CanonicalValidationPort;
import br.com.banco.spider.execution.retry.ControlledRetryExecutor;
import br.com.banco.spider.execution.retry.RetryPolicyCatalogPort;
import br.com.banco.spider.execution.retry.RetryPolicyDefinition;
import br.com.banco.spider.execution.route.IdempotencyClassification;
import br.com.banco.spider.execution.route.RetrySafety;
import br.com.banco.spider.execution.route.RouteResolverPort;
import br.com.banco.spider.execution.step.IntermediateStepOutputStore;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.WaitCreationService;
import br.com.banco.spider.execution.wait.WaitType;
import br.com.banco.spider.integration.binding.AdapterBindingResolverPort;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.integration.port.UniversalAdapterPort;
import br.com.banco.spider.integration.port.UniversalAdapterRequest;
import br.com.banco.spider.integration.port.UniversalAdapterResult;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Engine canônica multi-step linear com retry controlado (PROMPT-004).
 *
 * <p>Steps não executados após falha terminal são marcados {@code SKIPPED}.
 * Correlation no reuse: resultado persistido preserva correlação original.
 */
@Service
public class DefaultCanonicalExecutionEngine implements CanonicalExecutionEngine {

  private static final Logger log = LoggerFactory.getLogger(DefaultCanonicalExecutionEngine.class);

  private final CanonicalValidationPort validation;
  private final RouteResolverPort routeResolver;
  private final ExecutionPlanMaterializerPort materializer;
  private final AdapterBindingResolverPort bindingResolver;
  private final ReactiveExecutionPersistenceGateway persistence;
  private final IdempotencyKeyHashPort keyHashPort;
  private final ControlledRetryExecutor retryExecutor;
  private final StepInputMappingPort mappingPort;
  private final RetryPolicyCatalogPort retryPolicies;
  private final ExecutionStepStorePort stepStore;
  private final IntermediateStepOutputStore stepOutputs;
  private final WaitCreationService waitCreation;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final Duration executionBudget;
  private final br.com.banco.spider.governance.DefaultGovernanceResolutionContextProvider
      governanceContextProvider;
  private final br.com.banco.spider.execution.route.RouteDefinitionValidator routeValidator;

  @org.springframework.beans.factory.annotation.Autowired
  public DefaultCanonicalExecutionEngine(
      CanonicalValidationPort validation,
      RouteResolverPort routeResolver,
      ExecutionPlanMaterializerPort materializer,
      AdapterBindingResolverPort bindingResolver,
      ReactiveExecutionPersistenceGateway persistence,
      IdempotencyKeyHashPort keyHashPort,
      ControlledRetryExecutor retryExecutor,
      StepInputMappingPort mappingPort,
      RetryPolicyCatalogPort retryPolicies,
      ExecutionStepStorePort stepStore,
      IntermediateStepOutputStore stepOutputs,
      WaitCreationService waitCreation,
      IdentifierGenerator ids,
      SpiderClock clock,
      @Value("${spider.canonical.execution.budget:PT60S}") Duration executionBudget,
      org.springframework.beans.factory.ObjectProvider<
              br.com.banco.spider.governance.DefaultGovernanceResolutionContextProvider>
          governanceContextProvider,
      org.springframework.beans.factory.ObjectProvider<
              br.com.banco.spider.execution.route.RouteDefinitionValidator>
          routeValidatorProvider) {
    this(
        validation,
        routeResolver,
        materializer,
        bindingResolver,
        persistence,
        keyHashPort,
        retryExecutor,
        mappingPort,
        retryPolicies,
        stepStore,
        stepOutputs,
        waitCreation,
        ids,
        clock,
        executionBudget,
        governanceContextProvider.getIfAvailable(),
        routeValidatorProvider.getIfAvailable());
  }

  /** Construtor de teste / wiring explícito. */
  public DefaultCanonicalExecutionEngine(
      CanonicalValidationPort validation,
      RouteResolverPort routeResolver,
      ExecutionPlanMaterializerPort materializer,
      AdapterBindingResolverPort bindingResolver,
      ReactiveExecutionPersistenceGateway persistence,
      IdempotencyKeyHashPort keyHashPort,
      ControlledRetryExecutor retryExecutor,
      StepInputMappingPort mappingPort,
      RetryPolicyCatalogPort retryPolicies,
      ExecutionStepStorePort stepStore,
      IntermediateStepOutputStore stepOutputs,
      WaitCreationService waitCreation,
      IdentifierGenerator ids,
      SpiderClock clock,
      Duration executionBudget,
      br.com.banco.spider.governance.DefaultGovernanceResolutionContextProvider
          governanceContextProvider,
      br.com.banco.spider.execution.route.RouteDefinitionValidator routeValidator) {
    this.validation = validation;
    this.routeResolver = routeResolver;
    this.materializer = materializer;
    this.bindingResolver = bindingResolver;
    this.persistence = persistence;
    this.keyHashPort = keyHashPort;
    this.retryExecutor = retryExecutor;
    this.mappingPort = mappingPort;
    this.retryPolicies = retryPolicies;
    this.stepStore = stepStore;
    this.stepOutputs = stepOutputs;
    this.waitCreation = waitCreation;
    this.ids = ids;
    this.clock = clock;
    this.executionBudget = executionBudget;
    this.governanceContextProvider = governanceContextProvider;
    this.routeValidator =
        routeValidator != null
            ? routeValidator
            : new br.com.banco.spider.execution.route.RouteDefinitionValidator();
  }

  /** Construtor de teste com budget padrão (STATIC / sem Control Plane). */
  public DefaultCanonicalExecutionEngine(
      CanonicalValidationPort validation,
      RouteResolverPort routeResolver,
      ExecutionPlanMaterializerPort materializer,
      AdapterBindingResolverPort bindingResolver,
      ReactiveExecutionPersistenceGateway persistence,
      IdempotencyKeyHashPort keyHashPort,
      ControlledRetryExecutor retryExecutor,
      StepInputMappingPort mappingPort,
      RetryPolicyCatalogPort retryPolicies,
      ExecutionStepStorePort stepStore,
      IntermediateStepOutputStore stepOutputs,
      WaitCreationService waitCreation,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.validation = validation;
    this.routeResolver = routeResolver;
    this.materializer = materializer;
    this.bindingResolver = bindingResolver;
    this.persistence = persistence;
    this.keyHashPort = keyHashPort;
    this.retryExecutor = retryExecutor;
    this.mappingPort = mappingPort;
    this.retryPolicies = retryPolicies;
    this.stepStore = stepStore;
    this.stepOutputs = stepOutputs;
    this.waitCreation = waitCreation;
    this.ids = ids;
    this.clock = clock;
    this.executionBudget = Duration.ofSeconds(60);
    this.governanceContextProvider = null;
    this.routeValidator = new br.com.banco.spider.execution.route.RouteDefinitionValidator();
  }

  @Override
  public Mono<CanonicalExecutionResult> execute(CanonicalExecutionRequest request) {
    return execute(request, null);
  }

  @Override
  public Mono<CanonicalExecutionResult> execute(
      CanonicalExecutionRequest request, String ownerPrincipalRef) {
    log.info(
        "event=request_received executionId={} correlationId={}",
        request.execution().executionId(),
        request.trace().correlationId());

    ValidationOutcome validationOutcome =
        validation.validateRequest(request, OperationClass.QUERY);
    if (!validationOutcome.valid()) {
      return Mono.just(buildRejected(request, null, validationOutcome.errors()));
    }

    if (governanceContextProvider != null && governanceContextProvider.isControlPlaneActive()) {
      return governanceContextProvider
          .resolveForNewExecution(request)
          .flatMap(ctx -> executeResolved(request, ownerPrincipalRef, ctx))
          .onErrorResume(
              ex -> {
                log.info(
                    "event=context_resolution_failed reasonCode={}",
                    ex.getMessage() == null ? "GOVERNANCE" : ex.getMessage());
                return Mono.just(
                    buildRejected(
                        request,
                        null,
                        List.of(
                            error(
                                "GOVERNANCE_CONTEXT_FAILED",
                                "Control Plane context resolution failed",
                                ErrorCategory.RESOLUTION))));
              });
    }
    return executeResolved(request, ownerPrincipalRef, null);
  }

  private Mono<CanonicalExecutionResult> executeResolved(
      CanonicalExecutionRequest request,
      String ownerPrincipalRef,
      br.com.banco.spider.governance.GovernanceResolutionContext govCtx) {

    RouteResolverPort effectiveRouteResolver =
        govCtx == null
            ? routeResolver
            : new br.com.banco.spider.execution.route.DeterministicRouteResolver(
                govCtx.routeCatalog(), routeValidator);
    AdapterBindingResolverPort effectiveBinding =
        govCtx == null ? bindingResolver : govCtx.adapterBindingResolver();
    RetryPolicyCatalogPort effectiveRetry =
        govCtx == null ? retryPolicies : govCtx.retryPolicyCatalog();

    return effectiveRouteResolver
        .resolve(request)
        .flatMap(
            resolution -> {
              if (!resolution.selected()) {
                return persistEarlyReject(request, resolution.errors(), resolution.reasonCode().name());
              }
              ExecutionPlanMaterialization mat = materializer.materialize(request, resolution);
              if (!mat.success()) {
                return persistEarlyReject(request, mat.errors(), "PLAN_INVALID");
              }
              ExecutionPlan plan = mat.plan();
              ExecutionPlanNode entry = plan.orderedNodes().getFirst();

              String rawKey = request.execution().idempotencyKey();
              if (entry.idempotencyClassification() == IdempotencyClassification.REQUIRED
                  && (rawKey == null || rawKey.isBlank())) {
                return Mono.just(
                    buildRejected(
                        request,
                        summary(plan),
                        List.of(
                            error(
                                "IDEMPOTENCY_KEY_REQUIRED",
                                "Idempotency key is required by entry step",
                                ErrorCategory.CONTRACT))));
              }
              for (ExecutionPlanNode n : plan.orderedNodes()) {
                if (n.retrySafety() == RetrySafety.SAFE_WITH_IDEMPOTENCY_KEY
                    && (rawKey == null || rawKey.isBlank())) {
                  return Mono.just(
                      buildRejected(
                          request,
                          summary(plan),
                          List.of(
                              error(
                                  "IDEMPOTENCY_KEY_REQUIRED",
                                  "Idempotency key required by SAFE_WITH_IDEMPOTENCY_KEY step "
                                      + n.stepId(),
                                  ErrorCategory.CONTRACT))));
                }
              }

              boolean useKey =
                  rawKey != null
                      && !rawKey.isBlank()
                      && entry.idempotencyClassification() != IdempotencyClassification.NOT_SUPPORTED;
              String effectiveKey = useKey ? rawKey : null;
              IdempotencyScope scope =
                  new IdempotencyScope(
                      request.origin().originatorId(),
                      request.target().capability(),
                      request.target().operation(),
                      major(request.contract().contractVersion()));
              String scopeHash = useKey ? scope.scopeHash() : null;
              String keyHash = useKey ? keyHashPort.hash(effectiveKey) : null;

              return persistence
                  .reserveOrCreate(request, scope, effectiveKey, true, ownerPrincipalRef)
                  .flatMap(
                      reservation ->
                          handleReservation(
                              request,
                              plan,
                              reservation,
                              scopeHash,
                              keyHash,
                              effectiveKey,
                              govCtx,
                              effectiveBinding,
                              effectiveRetry));
            });
  }

  private Mono<CanonicalExecutionResult> handleReservation(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      IdempotencyReservationResult reservation,
      String scopeHash,
      String keyHash,
      String effectiveKey,
      br.com.banco.spider.governance.GovernanceResolutionContext govCtx,
      AdapterBindingResolverPort effectiveBinding,
      RetryPolicyCatalogPort effectiveRetry) {

    if (reservation.isConflict()
        || reservation.status() == IdempotencyReservationStatus.EXPIRED_REUSABLE_KEY) {
      return Mono.just(
          buildRejected(
              request,
              null,
              List.of(
                  error(
                      "IDEMPOTENCY_CONFLICT",
                      "Idempotency conflict or expired key",
                      ErrorCategory.IDEMPOTENCY))));
    }
    if (reservation.status() == IdempotencyReservationStatus.COMPLETED_SAME_REQUEST
        || reservation.status() == IdempotencyReservationStatus.FAILED_SAME_REQUEST) {
      return reusePersistedResult(reservation);
    }
    if (reservation.status() == IdempotencyReservationStatus.UNKNOWN_SAME_REQUEST) {
      return reuseUnknown(request, reservation);
    }
    if (reservation.status() == IdempotencyReservationStatus.IN_PROGRESS_SAME_REQUEST) {
      return reuseInProgress(request, reservation);
    }
    return continueNewExecution(
        request, plan, scopeHash, keyHash, effectiveKey, govCtx, effectiveBinding, effectiveRetry);
  }

  private Mono<CanonicalExecutionResult> continueNewExecution(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      String scopeHash,
      String keyHash,
      String effectiveKey,
      br.com.banco.spider.governance.GovernanceResolutionContext govCtx,
      AdapterBindingResolverPort effectiveBinding,
      RetryPolicyCatalogPort effectiveRetry) {

    String executionId = request.execution().executionId();
    ExecutionDeadline deadline = ExecutionDeadline.fromNow(clock, executionBudget);

    return persistence
        .findControl(executionId)
        .flatMap(
            opt -> {
              ExecutionControlRecord control = opt.orElseThrow();
              return persistence
                  .transition(
                      executionId,
                      ExecutionState.RECEIVED,
                      control.stateVersion(),
                      ExecutionState.VALIDATED,
                      "REQUEST_VALIDATED",
                      null,
                      null,
                      null,
                      null,
                      null)
                  .flatMap(
                      c1 ->
                          persistence.transition(
                              executionId,
                              ExecutionState.VALIDATED,
                              c1.stateVersion(),
                              ExecutionState.RESOLVED,
                              "ROUTE_SELECTED",
                              null,
                              null,
                              plan.routeRef().routeCode(),
                              plan.routeRef().routeVersion(),
                              null))
                  .flatMap(c2 -> persistence.persistPlan(plan, c2.stateVersion()))
                  .flatMap(
                      c3 -> {
                        if (govCtx != null && governanceContextProvider != null) {
                          try {
                            br.com.banco.spider.governance.ExecutionGovernanceFixation fixation =
                                governanceContextProvider.buildFixation(executionId, govCtx);
                            governanceContextProvider.persistFixation(fixation);
                            log.info(
                                "event=execution_fixation_created snapshotId={} reasonCode=OK",
                                fixation.snapshotId());
                          } catch (RuntimeException ex) {
                            log.info(
                                "event=execution_fixation_failed reasonCode={}",
                                ex.getMessage());
                            return Mono.just(
                                buildRejected(
                                    request,
                                    summary(plan),
                                    List.of(
                                        error(
                                            "GOVERNANCE_FIXATION_FAILED",
                                            "Failed to persist governance fixation",
                                            ErrorCategory.INTERNAL))));
                          }
                        }
                        return persistence
                            .markIdempotencyInProgress(scopeHash, keyHash)
                            .then(
                                persistence.transition(
                                    executionId,
                                    ExecutionState.PLANNED,
                                    c3.stateVersion(),
                                    ExecutionState.RUNNING,
                                    "STEPS_STARTED",
                                    TechnicalStatus.PENDING,
                                    null,
                                    null,
                                    null,
                                    null))
                            .flatMap(
                                running ->
                                    executeStepsSequentially(
                                            request,
                                            plan,
                                            deadline,
                                            effectiveKey,
                                            running,
                                            scopeHash,
                                            keyHash,
                                            effectiveBinding,
                                            effectiveRetry)
                                        .onErrorResume(
                                            ex -> {
                                              log.info(
                                                  "event=persistence_failure executionId={} reasonCode=ENGINE_ERROR",
                                                  executionId);
                                              return Mono.just(
                                                  buildRejected(
                                                      request,
                                                      summary(plan),
                                                      List.of(
                                                          error(
                                                              "ENGINE_INTERNAL",
                                                              "Execution failed internally",
                                                              ErrorCategory.INTERNAL))));
                                            }));
                      });
            });
  }

  private Mono<CanonicalExecutionResult> executeStepsSequentially(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      ExecutionDeadline deadline,
      String effectiveKey,
      ExecutionControlRecord running,
      String scopeHash,
      String keyHash,
      AdapterBindingResolverPort effectiveBinding,
      RetryPolicyCatalogPort effectiveRetry) {

    List<ExecutionPlanNode> nodes = plan.orderedNodes();
    return Flux.fromIterable(nodes)
        .concatMap(
            node ->
                executeOneStep(
                    request, plan, node, deadline, effectiveKey, effectiveBinding, effectiveRetry))
        .takeUntil(sr -> sr.stopRoute)
        .collectList()
        .flatMap(
            stepResults -> {
              StepRun last =
                  stepResults.isEmpty() ? null : stepResults.get(stepResults.size() - 1);
              if (last != null && last.stopRoute && last.waitingExternal) {
                return finalizeWaiting(request, plan, running, last, scopeHash, keyHash, deadline);
              }
              if (last != null && last.stopRoute && !last.success) {
                skipRemaining(request.execution().executionId(), nodes, last.node.orderedPosition());
                return finalizeFailure(request, plan, running, last, scopeHash, keyHash);
              }
              return finalizeSuccess(request, plan, running, stepResults, scopeHash, keyHash);
            });
  }

  private Mono<StepRun> executeOneStep(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      ExecutionPlanNode node,
      ExecutionDeadline deadline,
      String effectiveKey,
      AdapterBindingResolverPort effectiveBinding,
      RetryPolicyCatalogPort effectiveRetry) {

    log.info(
        "event=step_ready executionId={} stepId={}",
        request.execution().executionId(),
        node.stepId());

    JsonNode previous = null;
    if (!node.dependencies().isEmpty()) {
      previous =
          stepOutputs
              .get(request.execution().executionId(), node.dependencies().getFirst())
              .orElse(null);
    }
    var mapped =
        mappingPort.map(
            new StepInputMappingPort.MappingRequest(
                StepInputMappingKind.fromRef(node.inputMappingRef()),
                request.payload() != null ? request.payload().canonicalData() : null,
                previous));
    if (!mapped.success()) {
      log.info(
          "event=mapping_failure executionId={} stepId={} reasonCode={}",
          request.execution().executionId(),
          node.stepId(),
          mapped.error().code());
      return Mono.just(StepRun.fail(node, mapped.error()));
    }

    RetryPolicyDefinition policy =
        effectiveRetry
            .findByRef(node.effectivePolicyRefs().get("retry"))
            .orElseGet(() -> RetryPolicyDefinition.noRetry("none", "1.0"));

    String stepKey =
        effectiveKey == null
            ? null
            : effectiveKey + "::" + request.execution().executionId() + "::" + node.stepId();

    return effectiveBinding
        .resolve(node.adapterBindingRef())
        .flatMap(
            binding -> {
              if (!binding.resolved()) {
                return Mono.just(StepRun.fail(node, binding.errors().getFirst()));
              }
              UniversalAdapterPort adapter = binding.adapter();
              CanonicalPayload stepPayload = CanonicalPayload.of(mapped.canonicalData());
              return retryExecutor
                  .execute(
                      request.execution().executionId(),
                      node,
                      policy,
                      deadline,
                      stepKey,
                      adapter,
                      invId ->
                          UniversalAdapterRequest.builder()
                              .invocationId(invId)
                              .executionId(request.execution().executionId())
                              .stepId(node.stepId())
                              .attemptId("pending")
                              .invokedAt(clock.now())
                              .capabilityCode(node.capabilityCode())
                              .operationCode(node.operationCode())
                              .bindingRef(node.adapterBindingRef())
                              .inputContractRef(node.inputContractRef())
                              .outputContractRef(node.outputContractRef())
                              .trace(request.trace())
                              .idempotencyKey(stepKey)
                              .payload(stepPayload)
                              .build())
                  .map(
                      result -> {
                        if (result.stepState() == StepState.SUCCEEDED) {
                          JsonNode out =
                              result.adapterResult().outcome() != null
                                  ? result.adapterResult().outcome().canonicalData()
                                  : mapped.canonicalData();
                          if (out == null) {
                            out = mapped.canonicalData();
                          }
                          stepOutputs.put(
                              request.execution().executionId(), node.stepId(), out);
                          log.info(
                              "event=next_step_released executionId={} completedStep={}",
                              request.execution().executionId(),
                              node.stepId());
                          // mark next READY is done inside finishAttempt semantics — ensure next READY
                          releaseNext(request.execution().executionId(), plan, node);
                          return StepRun.ok(node, result);
                        }
                        if (result.waitingExternal()) {
                          return StepRun.waiting(node, result);
                        }
                        return StepRun.failStep(node, result);
                      });
            });
  }

  private void releaseNext(String executionId, ExecutionPlan plan, ExecutionPlanNode completed) {
    plan.orderedNodes().stream()
        .filter(n -> n.orderedPosition() == completed.orderedPosition() + 1)
        .findFirst()
        .ifPresent(
            next -> {
              var step = stepStore.find(executionId, next.stepId()).orElse(null);
              if (step != null && step.state() == StepState.PENDING) {
                stepStore.updateState(
                    executionId,
                    next.stepId(),
                    StepState.PENDING,
                    step.stateVersion(),
                    StepState.READY,
                    null,
                    null,
                    null,
                    null,
                    null,
                    clock.now());
              }
            });
  }

  private void skipRemaining(String executionId, List<ExecutionPlanNode> nodes, int failedPos) {
    for (ExecutionPlanNode n : nodes) {
      if (n.orderedPosition() > failedPos) {
        var step = stepStore.find(executionId, n.stepId()).orElse(null);
        if (step != null && (step.state() == StepState.PENDING || step.state() == StepState.READY)) {
          stepStore.updateState(
              executionId,
              n.stepId(),
              step.state(),
              step.stateVersion(),
              StepState.SKIPPED,
              null,
              null,
              "PREDECESSOR_FAILED",
              null,
              clock.now(),
              clock.now());
        }
      }
    }
  }

  private Mono<CanonicalExecutionResult> finalizeSuccess(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      ExecutionControlRecord running,
      List<StepRun> stepResults,
      String scopeHash,
      String keyHash) {
    Instant now = clock.now();
    StepRun last = stepResults.getLast();
    JsonNode finalData =
        stepOutputs
            .get(request.execution().executionId(), last.node.stepId())
            .orElse(null);
    CanonicalOutcome outcome =
        last.retryResult != null && last.retryResult.adapterResult().outcome() != null
            ? new CanonicalOutcome(
                TechnicalStatus.SUCCESS,
                last.retryResult.adapterResult().outcome().businessOutcome(),
                finalData != null
                    ? finalData
                    : last.retryResult.adapterResult().outcome().canonicalData())
            : new CanonicalOutcome(TechnicalStatus.SUCCESS, null, finalData);

    List<EvidenceReference> evidences = aggregateEvidence(stepResults);
    List<CanonicalError> errors = aggregateErrors(stepResults);

    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(request.contract())
            .execution(
                new ExecutionSummary(
                    request.execution().executionId(),
                    ExecutionState.SUCCEEDED,
                    running.startedAt() != null ? running.startedAt() : now,
                    now,
                    now))
            .contextRef(ResultContextReference.from(request.contextRef()))
            .trace(ResultTraceDescriptor.from(request.trace()))
            .resolution(summary(plan))
            .outcome(outcome)
            .errors(errors)
            .evidenceRefs(evidences)
            .build();

    return persistence
        .transition(
            request.execution().executionId(),
            ExecutionState.RUNNING,
            running.stateVersion(),
            ExecutionState.SUCCEEDED,
            "ALL_STEPS_SUCCEEDED",
            TechnicalStatus.SUCCESS,
            null,
            null,
            null,
            null)
        .then(
            persistence.persistTerminalResult(
                result, IdempotencyRecordState.COMPLETED, scopeHash, keyHash))
        .thenReturn(result);
  }

  private Mono<CanonicalExecutionResult> finalizeFailure(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      ExecutionControlRecord running,
      StepRun last,
      String scopeHash,
      String keyHash) {
    Instant now = clock.now();
    ExecutionState state =
        last.retryResult != null
                && last.retryResult.mapped().state() == ExecutionState.TIMED_OUT
            ? ExecutionState.TIMED_OUT
            : ExecutionState.FAILED;
    TechnicalStatus tech = TechnicalStatus.FAILURE;
    List<CanonicalError> errors = new ArrayList<>();
    if (last.mappingError != null) {
      errors.add(last.mappingError);
    }
    if (last.retryResult != null && last.retryResult.adapterResult() != null) {
      errors.addAll(last.retryResult.adapterResult().errors());
    }

    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(request.contract())
            .execution(
                new ExecutionSummary(
                    request.execution().executionId(),
                    state,
                    running.startedAt(),
                    now,
                    now))
            .contextRef(ResultContextReference.from(request.contextRef()))
            .trace(ResultTraceDescriptor.from(request.trace()))
            .resolution(summary(plan))
            .outcome(CanonicalOutcome.technical(tech))
            .errors(errors)
            .evidenceRefs(aggregateEvidence(List.of(last)))
            .build();

    log.info(
        "event=route_stopped executionId={} stepId={} state={}",
        request.execution().executionId(),
        last.node.stepId(),
        state);

    return persistence
        .transition(
            request.execution().executionId(),
            ExecutionState.RUNNING,
            running.stateVersion(),
            state,
            "STEP_TERMINAL_FAILURE",
            tech,
            null,
            null,
            null,
            null)
        .then(
            persistence.persistTerminalResult(
                result, IdempotencyRecordState.FAILED_REUSABLE, scopeHash, keyHash))
        .thenReturn(result);
  }

  private Mono<CanonicalExecutionResult> finalizeWaiting(
      CanonicalExecutionRequest request,
      ExecutionPlan plan,
      ExecutionControlRecord running,
      StepRun last,
      String scopeHash,
      String keyHash,
      ExecutionDeadline deadline) {
    Instant now = clock.now();
    WaitType waitType =
        last.retryResult != null
                && last.retryResult.adapterResult().dispositionMode()
                    == AdapterDispositionMode.UNKNOWN
            ? WaitType.UNKNOWN_OUTCOME_RECONCILIATION
            : WaitType.ASYNC_COMPLETION;

    var created =
        waitCreation.createFromAdapterResult(
            last.retryResult.adapterResult(),
            last.node,
            deadline,
            last.retryResult.adapterResult().attemptId(),
            waitType);
    if (!created.success()) {
      skipRemaining(request.execution().executionId(), plan.orderedNodes(), last.node.orderedPosition());
      return finalizeFailure(
          request,
          plan,
          running,
          StepRun.fail(last.node, created.error()),
          scopeHash,
          keyHash);
    }

    IdempotencyRecordState idemState =
        waitType == WaitType.UNKNOWN_OUTCOME_RECONCILIATION
            ? IdempotencyRecordState.UNKNOWN
            : IdempotencyRecordState.IN_PROGRESS;

    CanonicalExecutionResult result =
        CanonicalExecutionResult.builder()
            .contract(request.contract())
            .execution(
                new ExecutionSummary(
                    request.execution().executionId(),
                    ExecutionState.WAITING_EXTERNAL,
                    running.startedAt(),
                    now,
                    now))
            .contextRef(ResultContextReference.from(request.contextRef()))
            .trace(ResultTraceDescriptor.from(request.trace()))
            .resolution(summary(plan))
            .outcome(CanonicalOutcome.technical(TechnicalStatus.PENDING))
            .errors(
                last.retryResult != null && last.retryResult.adapterResult() != null
                    ? last.retryResult.adapterResult().errors()
                    : List.of())
            .evidenceRefs(aggregateEvidence(List.of(last)))
            .build();

    log.info(
        "event=execution_waiting executionId={} stepId={} waitId={}",
        request.execution().executionId(),
        last.node.stepId(),
        created.waitRecord().waitId());

    return persistence
        .transition(
            request.execution().executionId(),
            ExecutionState.RUNNING,
            running.stateVersion(),
            ExecutionState.WAITING_EXTERNAL,
            "STEP_WAITING_EXTERNAL",
            TechnicalStatus.PENDING,
            null,
            null,
            null,
            last.retryResult != null
                ? last.retryResult.adapterResult().dispositionMode().name()
                : "UNKNOWN")
        .then(
            persistence.persistTerminalResult(result, idemState, scopeHash, keyHash))
        .thenReturn(result);
  }

  private List<EvidenceReference> aggregateEvidence(List<StepRun> runs) {
    LinkedHashSet<String> seen = new LinkedHashSet<>();
    List<EvidenceReference> out = new ArrayList<>();
    for (StepRun r : runs) {
      if (r.retryResult == null || r.retryResult.adapterResult() == null) {
        continue;
      }
      for (EvidenceReference e : r.retryResult.adapterResult().evidenceRefs()) {
        if (seen.add(e.evidenceId())) {
          out.add(e);
        }
      }
    }
    return out;
  }

  private List<CanonicalError> aggregateErrors(List<StepRun> runs) {
    List<CanonicalError> out = new ArrayList<>();
    for (StepRun r : runs) {
      if (r.retryResult != null
          && r.retryResult.adapterResult() != null
          && r.retryResult.adapterResult().errors() != null) {
        out.addAll(r.retryResult.adapterResult().errors());
      }
    }
    return out;
  }

  private Mono<CanonicalExecutionResult> reusePersistedResult(
      IdempotencyReservationResult reservation) {
    if (reservation.resultRef() == null) {
      return Mono.error(new IllegalStateException("Missing resultRef for reuse"));
    }
    return persistence
        .findResult(reservation.resultRef())
        .flatMap(
            opt ->
                opt.map(persistence::loadResult)
                    .orElseGet(
                        () -> Mono.error(new IllegalStateException("Persisted result not found"))));
  }

  private Mono<CanonicalExecutionResult> reuseInProgress(
      CanonicalExecutionRequest request, IdempotencyReservationResult reservation) {
    String executionId = reservation.existingExecutionId();
    return persistence
        .findControl(executionId)
        .map(
            opt -> {
              ExecutionControlRecord control = opt.orElse(null);
              ExecutionState state =
                  control != null
                      ? control.state()
                      : (reservation.existingState() != null
                          ? reservation.existingState()
                          : ExecutionState.RUNNING);
              Instant now = clock.now();
              return CanonicalExecutionResult.builder()
                  .contract(request.contract())
                  .execution(new ExecutionSummary(executionId, state, null, null, now))
                  .contextRef(ResultContextReference.from(request.contextRef()))
                  .trace(ResultTraceDescriptor.from(request.trace()))
                  .resolution(
                      control != null && control.routeCode() != null
                          ? new ResolutionSummary(
                              control.routeCode(), control.routeVersion(), control.planId())
                          : null)
                  .outcome(CanonicalOutcome.technical(TechnicalStatus.PENDING))
                  .errors(List.of())
                  .evidenceRefs(List.of())
                  .build();
            });
  }

  private Mono<CanonicalExecutionResult> reuseUnknown(
      CanonicalExecutionRequest request, IdempotencyReservationResult reservation) {
    if (reservation.resultRef() != null) {
      return reusePersistedResult(reservation);
    }
    Instant now = clock.now();
    return Mono.just(
        CanonicalExecutionResult.builder()
            .contract(request.contract())
            .execution(
                new ExecutionSummary(
                    reservation.existingExecutionId(),
                    ExecutionState.WAITING_EXTERNAL,
                    null,
                    now,
                    now))
            .contextRef(ResultContextReference.from(request.contextRef()))
            .trace(ResultTraceDescriptor.from(request.trace()))
            .outcome(CanonicalOutcome.technical(TechnicalStatus.PENDING))
            .errors(
                List.of(
                    error(
                        "IDEMPOTENCY_UNKNOWN_REUSE",
                        "Previous adapter disposition was inconclusive",
                        ErrorCategory.INTERNAL)))
            .evidenceRefs(List.of())
            .build());
  }

  private Mono<CanonicalExecutionResult> persistEarlyReject(
      CanonicalExecutionRequest request, List<CanonicalError> errors, String reason) {
    return persistence
        .reserveOrCreate(
            request,
            new IdempotencyScope(
                request.origin().originatorId(),
                request.target().capability(),
                request.target().operation(),
                major(request.contract().contractVersion())),
            null,
            true)
        .flatMap(
            r ->
                persistence
                    .findControl(request.execution().executionId())
                    .flatMap(
                        opt -> {
                          ExecutionControlRecord c = opt.orElseThrow();
                          return persistence
                              .transition(
                                  c.executionId(),
                                  ExecutionState.RECEIVED,
                                  c.stateVersion(),
                                  ExecutionState.VALIDATED,
                                  "REQUEST_VALIDATED",
                                  null,
                                  null,
                                  null,
                                  null,
                                  null)
                              .flatMap(
                                  c2 ->
                                      persistence.transition(
                                          c2.executionId(),
                                          ExecutionState.VALIDATED,
                                          c2.stateVersion(),
                                          ExecutionState.REJECTED,
                                          reason,
                                          TechnicalStatus.REJECTED,
                                          null,
                                          null,
                                          null,
                                          null));
                        }))
        .thenReturn(buildRejected(request, null, errors));
  }

  private CanonicalExecutionResult buildRejected(
      CanonicalExecutionRequest request,
      ResolutionSummary resolution,
      List<CanonicalError> errors) {
    Instant now = clock.now();
    return CanonicalExecutionResult.builder()
        .contract(request.contract())
        .execution(
            new ExecutionSummary(
                request.execution().executionId(), ExecutionState.REJECTED, null, now, now))
        .contextRef(ResultContextReference.from(request.contextRef()))
        .trace(ResultTraceDescriptor.from(request.trace()))
        .resolution(resolution)
        .outcome(CanonicalOutcome.technical(TechnicalStatus.REJECTED))
        .errors(errors == null ? List.of() : errors)
        .evidenceRefs(List.of())
        .build();
  }

  private static ResolutionSummary summary(ExecutionPlan plan) {
    return new ResolutionSummary(
        plan.routeRef().routeCode(), plan.routeRef().routeVersion(), plan.planId());
  }

  private static String major(String version) {
    if (version == null || version.isBlank()) {
      return "0";
    }
    int dot = version.indexOf('.');
    return dot < 0 ? version : version.substring(0, dot);
  }

  private static CanonicalError error(String code, String message, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("canonical_engine", null, null, null))
        .build();
  }

  private record StepRun(
      ExecutionPlanNode node,
      boolean success,
      boolean stopRoute,
      boolean waitingExternal,
      ControlledRetryExecutor.StepInvokeResult retryResult,
      CanonicalError mappingError) {

    static StepRun ok(ExecutionPlanNode node, ControlledRetryExecutor.StepInvokeResult r) {
      return new StepRun(node, true, false, false, r, null);
    }

    static StepRun waiting(ExecutionPlanNode node, ControlledRetryExecutor.StepInvokeResult r) {
      return new StepRun(node, false, true, true, r, null);
    }

    static StepRun failStep(ExecutionPlanNode node, ControlledRetryExecutor.StepInvokeResult r) {
      return new StepRun(node, false, true, false, r, null);
    }

    static StepRun fail(ExecutionPlanNode node, CanonicalError err) {
      return new StepRun(node, false, true, false, null, err);
    }
  }
}
