package br.com.banco.spider.context.application;

import br.com.banco.spider.application.canonical.SubmitCanonicalExecutionUseCase;
import br.com.banco.spider.application.security.AuthenticatedOriginator;
import br.com.banco.spider.application.security.AuthorizationDecision;
import br.com.banco.spider.application.security.CanonicalIngressSecurityContext;
import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalPayload;
import br.com.banco.spider.canonical.contract.ContextReference;
import br.com.banco.spider.canonical.contract.ContractDescriptor;
import br.com.banco.spider.canonical.contract.ExecutionIdentity;
import br.com.banco.spider.canonical.contract.ExecutionPolicyReference;
import br.com.banco.spider.canonical.contract.OriginDescriptor;
import br.com.banco.spider.canonical.contract.TargetDescriptor;
import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.context.capability.CapabilityResolution;
import br.com.banco.spider.context.capability.CapabilityResolutionStatus;
import br.com.banco.spider.context.capability.CapabilityResolver;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.BusinessIntentCatalog;
import br.com.banco.spider.context.domain.ContextGuardDecision;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.IntentRouteResolution;
import br.com.banco.spider.context.planning.ContextExecutionPlan;
import br.com.banco.spider.context.planning.ContextExecutionPlanStatus;
import br.com.banco.spider.context.planning.ExecutionPlanResolver;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import reactor.core.publisher.Mono;

/** Orquestra o Context Plane sem criar atalho para a engine ou para autorização canônica. */
public final class ContextIntelligenceService {

  private static final SecureRandom RANDOM = new SecureRandom();

  private final BusinessIntentCatalog catalog;
  private final ContextPolicyGuard guard;
  private final ExecutionPlanResolver planResolver;
  private final CapabilityResolver capabilityResolver;
  private final DeterministicIntentRouter router;
  private final ContextDecisionStore store;
  private final SubmitCanonicalExecutionUseCase canonicalSubmit;
  private final OperationalEventPublisher events;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final ObjectMapper mapper;

  public ContextIntelligenceService(
      BusinessIntentCatalog catalog,
      ContextPolicyGuard guard,
      ExecutionPlanResolver planResolver,
      CapabilityResolver capabilityResolver,
      DeterministicIntentRouter router,
      ContextDecisionStore store,
      SubmitCanonicalExecutionUseCase canonicalSubmit,
      OperationalEventPublisher events,
      IdentifierGenerator ids,
      SpiderClock clock,
      ObjectMapper mapper) {
    this.catalog = catalog;
    this.guard = guard;
    this.planResolver = planResolver;
    this.capabilityResolver = capabilityResolver;
    this.router = router;
    this.store = store;
    this.canonicalSubmit = canonicalSubmit;
    this.events = events;
    this.ids = ids;
    this.clock = clock;
    this.mapper = mapper;
  }

  public BusinessIntentCatalog catalog() {
    return catalog;
  }

  public ContextDecisionRecord resolve(IntentContract contract, String principalRef) {
    return resolve(contract, principalRef, null);
  }

  public ContextDecisionRecord resolve(
      IntentContract contract,
      String principalRef,
      ContextInterpretationEvidence interpretation) {
    Instant createdAt = clock.now();
    var guardResult = guard.evaluate(contract, principalRef != null && !principalRef.isBlank());
    ContextExecutionPlan plan = planResolver.resolve(contract, guardResult).orElse(null);
    List<CapabilityResolution> capabilities = capabilityResolver.resolve(plan);
    IntentRouteResolution route =
        router.resolvePrimaryRoute(plan, capabilities, guardResult).orElse(null);
    String decisionId = ids.nextId("ctxd");
    ContextDecisionRecord record =
        new ContextDecisionRecord(
            decisionId,
            principalRef,
            contract,
            guardResult,
            plan,
            capabilities,
            route,
            createdAt,
            null,
            null,
            null,
            interpretation,
            journey(
                contract,
                guardResult,
                plan,
                capabilities,
                route,
                createdAt,
                interpretation));
    store.save(record);
    emitPlanningEvents(decisionId, contract, guardResult, plan, capabilities);
    return record;
  }

  public Mono<ContextExecutionOutcome> execute(
      String decisionId, IntentContract contract, AuthenticatedOriginator originator) {
    Optional<ContextDecisionRecord> preview = store.findByDecisionId(decisionId);
    if (preview.isEmpty()
        || originator == null
        || !preview.get().principalRef().equals(originator.principalRef())
        || !preview.get().intentContract().equals(contract)) {
      var rejected =
          new ContextPolicyGuard.GuardResult(
              ContextGuardDecision.POLICY_REJECTED,
              "CONFIRMED_INTENT_DIFFERS_FROM_PREVIEW",
              ContextPolicyGuard.POLICY_REF);
      return Mono.just(new ContextExecutionOutcome(false, preview.orElse(null), rejected, null));
    }

    var guardResult = guard.evaluate(contract, true);
    ContextExecutionPlan plan = planResolver.resolve(contract, guardResult).orElse(null);
    List<CapabilityResolution> capabilities = capabilityResolver.resolve(plan);
    IntentRouteResolution route =
        router.resolvePrimaryRoute(plan, capabilities, guardResult).orElse(null);
    if (!guardResult.accepted()) {
      return Mono.just(new ContextExecutionOutcome(false, preview.get(), guardResult, null));
    }
    if (plan == null
        || plan.status() != ContextExecutionPlanStatus.READY
        || route == null) {
      var planRejected =
          new ContextPolicyGuard.GuardResult(
              ContextGuardDecision.POLICY_REJECTED,
              plan == null
                  ? "EXECUTION_PLAN_NOT_RESOLVED"
                  : "EXECUTION_PLAN_" + plan.status().name(),
              guardResult.policyRef());
      return Mono.just(new ContextExecutionOutcome(false, preview.get(), planRejected, null));
    }
    if (!route.executable()) {
      var notExecutable =
          new ContextPolicyGuard.GuardResult(
              ContextGuardDecision.POLICY_REJECTED,
              "INTENT_NOT_EXECUTABLE_IN_CTX001",
              guardResult.policyRef());
      return Mono.just(new ContextExecutionOutcome(false, preview.get(), notExecutable, null));
    }

    String executionId = ids.nextId("exec");
    String correlationId = ids.nextId("corr");
    Instant submittedAt = clock.now();
    emitContextEvents(
        executionId,
        correlationId,
        contract,
        plan,
        capabilities,
        route,
        guardResult,
        preview.get().interpretation());
    CanonicalExecutionRequest canonical =
        canonicalRequest(
            executionId,
            correlationId,
            submittedAt,
            preview.get().decisionId(),
            contract,
            plan,
            route,
            originator);
    var command =
        new SubmitCanonicalExecutionUseCase.SubmitCanonicalExecutionCommand(
            canonical,
            CanonicalIngressSecurityContext.from(originator, AuthorizationDecision.PERMIT),
            originator,
            canonical.trace(),
            canonical.execution().idempotencyKey(),
            submittedAt);

    return canonicalSubmit
        .submit(command)
        .map(
            submitOutcome -> {
              String state =
                  submitOutcome.success()
                      ? submitOutcome.result().state().name()
                      : "REJECTED";
              ContextDecisionRecord executed =
                  preview.get().withExecution(executionId, state, clock.now());
              store.save(executed);
              return new ContextExecutionOutcome(
                  submitOutcome.success(), executed, guardResult, submitOutcome);
            });
  }

  public Optional<ContextDecisionRecord> findByExecutionId(
      String executionId, String principalRef) {
    return store
        .findByExecutionId(executionId)
        .filter(record -> record.principalRef().equals(principalRef));
  }

  private CanonicalExecutionRequest canonicalRequest(
      String executionId,
      String correlationId,
      Instant submittedAt,
      String decisionId,
      IntentContract contract,
      ContextExecutionPlan plan,
      IntentRouteResolution route,
      AuthenticatedOriginator originator) {
    ObjectNode data = mapper.createObjectNode();
    data.put("mockScenario", route.mockScenario());
    data.put("contextDecision", "DETERMINISTIC");
    data.put("contextDecisionId", decisionId);
    data.put("contextPlanId", plan.planId());
    data.put("contextPlanType", plan.planType());
    data.put("intent", contract.intent());
    data.set("entities", mapper.valueToTree(contract.entities()));
    return CanonicalExecutionRequest.builder()
        .contract(new ContractDescriptor("1.0", "1.0.0"))
        .execution(new ExecutionIdentity(executionId, submittedAt, "context-" + executionId))
        .contextRef(
            new ContextReference(
                "context:" + contract.domain().toLowerCase(),
                "intent:" + contract.intent().toLowerCase(),
                "capability:" + route.capabilityRef().toLowerCase(),
                "product:context-intelligence",
                "journey:mock"))
        .origin(
            new OriginDescriptor(
                originator.channel(), originator.originatorId(), "context:" + route.routeRef()))
        .trace(new TraceDescriptor(correlationId, newTraceparent(), null))
        .target(new TargetDescriptor("mock", route.targetOperation()))
        .payload(CanonicalPayload.of(data))
        .executionPolicy(ExecutionPolicyReference.empty())
        .build();
  }

  private void emitContextEvents(
      String executionId,
      String correlationId,
      IntentContract contract,
      ContextExecutionPlan plan,
      List<CapabilityResolution> capabilities,
      IntentRouteResolution route,
      ContextPolicyGuard.GuardResult guardResult,
      ContextInterpretationEvidence interpretation) {
    if (interpretation != null) {
      publish(
          OperationalEventType.AI_INTERPRETATION_SUCCEEDED,
          executionId,
          correlationId,
          OperationalEventAttributes.builder()
              .reasonCode("AI_INTERPRETATION_USED_BY_EXECUTION")
              .put("provider", interpretation.provider())
              .put("model", interpretation.model())
              .put("interpretationStatus", "SUCCEEDED")
              .build());
    }
    publish(
        OperationalEventType.INTENT_CREATED,
        executionId,
        correlationId,
        OperationalEventAttributes.builder()
            .put("intent", contract.intent())
            .put("domain", contract.domain())
            .put("provenance", contract.provenance().source().name())
            .build());
    publish(
        OperationalEventType.INTENT_VALIDATED,
        executionId,
        correlationId,
        OperationalEventAttributes.builder()
            .policyRef(guardResult.policyRef())
            .reasonCode(guardResult.reasonCode())
            .build());
    publish(
        OperationalEventType.EXECUTION_PLAN_RESOLVED,
        executionId,
        correlationId,
        OperationalEventAttributes.builder()
            .reasonCode(plan.status().name())
            .put("planId", plan.planId())
            .put("planType", plan.planType())
            .put("planStatus", plan.status().name())
            .build());
    for (CapabilityResolution capability : capabilities) {
      publish(
          capability.status() == CapabilityResolutionStatus.RESOLVED
              ? OperationalEventType.CAPABILITY_RESOLVED
              : OperationalEventType.CAPABILITY_UNAVAILABLE,
          executionId,
          correlationId,
          OperationalEventAttributes.builder()
              .reasonCode(capability.status().name())
              .put("planId", plan.planId())
              .put("capabilityRef", capability.capabilityId())
              .routeCode(
                  capability.selectedRoute() == null
                      ? null
                      : capability.selectedRoute().routeRef())
              .build());
    }
    publish(
        OperationalEventType.ROUTE_RESOLVED,
        executionId,
        correlationId,
        OperationalEventAttributes.builder()
            .routeCode(route.routeRef())
            .put("capabilityRef", route.capabilityRef())
            .build());
  }

  private void emitPlanningEvents(
      String decisionId,
      IntentContract contract,
      ContextPolicyGuard.GuardResult guardResult,
      ContextExecutionPlan plan,
      List<CapabilityResolution> capabilities) {
    if (plan == null) {
      OperationalEventEmit.publish(
          events,
          OperationalEventEmit.draft(
              OperationalEventType.EXECUTION_PLAN_REJECTED,
              decisionId,
              decisionId,
              "context-planning",
              OperationalEventOutcome.REJECTED,
              null,
              OperationalEventAttributes.builder()
                  .reasonCode(guardResult.reasonCode())
                  .put("intent", contract == null ? null : contract.intent())
                  .build()));
      return;
    }
    publish(
        OperationalEventType.EXECUTION_PLAN_RESOLVED,
        decisionId,
        decisionId,
        OperationalEventAttributes.builder()
            .reasonCode(plan.status().name())
            .put("intent", plan.intent())
            .put("planId", plan.planId())
            .put("planType", plan.planType())
            .put("planStatus", plan.status().name())
            .build());
    for (CapabilityResolution capability : capabilities) {
      OperationalEventOutcome outcome =
          capability.status() == CapabilityResolutionStatus.RESOLVED
              ? OperationalEventOutcome.SUCCESS
              : OperationalEventOutcome.REJECTED;
      OperationalEventEmit.publish(
          events,
          OperationalEventEmit.draft(
              capability.status() == CapabilityResolutionStatus.RESOLVED
                  ? OperationalEventType.CAPABILITY_RESOLVED
                  : OperationalEventType.CAPABILITY_UNAVAILABLE,
              decisionId,
              decisionId,
              "capability-resolution",
              outcome,
              null,
              OperationalEventAttributes.builder()
                  .reasonCode(capability.status().name())
                  .put("planId", plan.planId())
                  .put("capabilityRef", capability.capabilityId())
                  .routeCode(
                      capability.selectedRoute() == null
                          ? null
                          : capability.selectedRoute().routeRef())
                  .build()));
    }
  }

  private void publish(
      OperationalEventType type,
      String executionId,
      String correlationId,
      OperationalEventAttributes attributes) {
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type,
            executionId,
            correlationId,
            "context-intelligence",
            OperationalEventOutcome.SUCCESS,
            null,
            attributes));
  }

  private static List<ContextJourneyStage> journey(
      IntentContract contract,
      ContextPolicyGuard.GuardResult guard,
      ContextExecutionPlan plan,
      List<CapabilityResolution> capabilities,
      IntentRouteResolution route,
      Instant at,
      ContextInterpretationEvidence interpretation) {
    if (contract == null) {
      return List.of(
          new ContextJourneyStage(
              "intent-contract",
              "Intent construído",
              "CONTEXT",
              "FAILED",
              "O Intent Contract não pôde ser construído.",
              at,
              Map.of("decision", guard.decision().name(), "reasonCode", guard.reasonCode())));
    }
    ContextJourneyStage objective =
        new ContextJourneyStage(
            interpretation == null ? "objective-selected" : "objective-received",
            interpretation == null ? "Objetivo selecionado" : "Objetivo recebido",
            "CONTEXT",
            "SUCCEEDED",
            interpretation == null
                ? "O objetivo "
                    + contract.objective()
                    + " foi selecionado no domínio "
                    + contract.domain()
                    + "."
                : "O objetivo em linguagem natural foi recebido e redigido antes da interpretação.",
            at,
            interpretation == null
                ? Map.of("objective", contract.objective(), "domain", contract.domain())
                : Map.of(
                    "requestedObjective",
                    interpretation.requestedObjective(),
                    "redactedFields",
                    Integer.toString(interpretation.redactedFieldsCount())));
    ContextJourneyStage aiInterpreted =
        interpretation == null
            ? null
            : new ContextJourneyStage(
                "ai-interpreted",
                "IA interpretou contexto",
                "CONTEXT",
                "SUCCEEDED",
                "A IA produziu uma decisão estruturada de intenção; nenhuma rota ou execução foi decidida pelo modelo.",
                at,
                interpretationDetails(interpretation));
    ContextJourneyStage intent =
        new ContextJourneyStage(
            "intent-created",
            "Intent construído",
            "CONTEXT",
            "SUCCEEDED",
            "O objetivo selecionado foi convertido para o contrato de intenção "
                + contract.intent()
                + ", pertencente ao domínio "
                + contract.domain()
                + ".",
            at,
            Map.of(
                "intent",
                contract.intent(),
                "schemaVersion",
                contract.schemaVersion(),
                "provenance",
                contract.provenance().source().name(),
                "confidence",
                contract.confidence().toPlainString()));
    ContextJourneyStage policy =
        new ContextJourneyStage(
            "policy-validated",
            "Política validada",
            "CONTEXT",
            guard.accepted() ? "SUCCEEDED" : "REJECTED",
            guard.accepted()
                ? "O Context Guard verificou o contrato, as restrições e a política de mutação. A intenção foi aceita como "
                    + (Boolean.TRUE.equals(contract.constraints().readOnly())
                        ? "somente consulta."
                        : "operação restrita.")
                : "O Context Guard bloqueou o contrato antes do Core: "
                    + guard.reasonCode()
                    + ".",
            at,
            Map.of(
                "decision",
                guard.decision().name(),
                "policyRef",
                guard.policyRef(),
                "reasonCode",
                guard.reasonCode()));
    List<ContextJourneyStage> stages = new java.util.ArrayList<>();
    stages.add(objective);
    if (aiInterpreted != null) {
      stages.add(aiInterpreted);
    }
    stages.add(intent);
    stages.add(policy);
    if (plan == null) {
      return List.copyOf(stages);
    }

    stages.add(
        new ContextJourneyStage(
            "execution-plan-resolved",
            "Plano determinado",
            "CONTEXT",
            "SUCCEEDED",
            "O Plan Resolver determinístico compôs o plano "
                + plan.planType()
                + " sem participação da IA.",
            at,
            Map.of(
                "planId", plan.planId(),
                "planType", plan.planType(),
                "planStatus", plan.status().name(),
                "statusReasons", plan.statusReasons().toString(),
                "stepCount", Integer.toString(plan.steps().size()))));
    long available =
        capabilities.stream()
            .filter(item -> item.status() == CapabilityResolutionStatus.RESOLVED)
            .count();
    stages.add(
        new ContextJourneyStage(
            "capabilities-resolved",
            "Capabilities resolvidas",
            "CONTEXT",
            "SUCCEEDED",
            "O Capability Resolver avaliou "
                + capabilities.size()
                + " competências; "
                + available
                + " possuem resolução disponível.",
            at,
            Map.of(
                "planId", plan.planId(),
                "resolvedCapabilities", Long.toString(available),
                "unavailableCapabilities",
                    Long.toString(capabilities.size() - available))));

    for (CapabilityResolution capability : capabilities) {
      stages.add(
          new ContextJourneyStage(
              "plan-capability-" + capability.stepId(),
              capability.capabilityId(),
              "PLAN",
              capability.status() == CapabilityResolutionStatus.RESOLVED
                  ? "SUCCEEDED"
                  : "NOT_REACHED",
              capability.status() == CapabilityResolutionStatus.RESOLVED
                  ? "A capability foi resolvida para uma rota elegível; ela ainda não foi executada."
                  : "A capability obrigatória não possui executor disponível neste boundary.",
              at,
              capabilityDetails(capability)));
    }
    if (route != null) {
      stages.add(
          new ContextJourneyStage(
              "route-resolved",
              "Rota determinada",
              "PLAN",
              "SUCCEEDED",
              "A rota "
                  + route.routeRef()
                  + " foi selecionada depois da resolução da capability "
                  + route.capabilityRef()
                  + ".",
              at,
              Map.of(
                  "capabilityRef",
                  route.capabilityRef(),
                  "routeRef",
                  route.routeRef(),
                  "executionAvailability",
                  route.executable() ? "CTX003_END_TO_END" : "PREVIEW_ONLY",
                  "policyRef",
                  route.policyRef())));
    }
    return List.copyOf(stages);
  }

  private static Map<String, String> capabilityDetails(CapabilityResolution capability) {
    Map<String, String> details = new LinkedHashMap<>();
    details.put("capabilityRef", capability.capabilityId());
    details.put("description", capability.description());
    details.put("reason", capability.reason());
    details.put("inputContract", String.valueOf(capability.inputContract()));
    details.put("outputContract", String.valueOf(capability.outputContract()));
    details.put("mutationType", capability.mutationType().name());
    details.put("availability", capability.availability().name());
    details.put("resolutionStatus", capability.status().name());
    if (capability.selectedRoute() != null) {
      details.put("routeRef", capability.selectedRoute().routeRef());
      details.put("adapterRef", capability.selectedRoute().adapterRef());
      details.put("targetOperation", capability.selectedRoute().targetOperation());
    }
    return Map.copyOf(details);
  }

  private static Map<String, String> interpretationDetails(
      ContextInterpretationEvidence interpretation) {
    Map<String, String> details = new LinkedHashMap<>();
    details.put("requestedObjective", interpretation.requestedObjective());
    details.put("intent", interpretation.intent());
    details.put("domain", interpretation.domain());
    details.put("extractedEntities", interpretation.extractedEntities().toString());
    details.put("missingContext", interpretation.missingContext().toString());
    details.put("confidence", interpretation.confidence().toPlainString());
    details.put("provider", interpretation.provider());
    details.put("model", interpretation.model());
    details.put("schemaVersion", interpretation.schemaVersion());
    details.put("promptVersion", interpretation.promptVersion());
    details.put("latencyMs", Long.toString(interpretation.latencyMs()));
    if (interpretation.usage().inputTokens() != null) {
      details.put("inputTokens", interpretation.usage().inputTokens().toString());
    }
    if (interpretation.usage().outputTokens() != null) {
      details.put("outputTokens", interpretation.usage().outputTokens().toString());
    }
    if (interpretation.usage().totalTokens() != null) {
      details.put("totalTokens", interpretation.usage().totalTokens().toString());
    }
    return Map.copyOf(details);
  }

  private static String newTraceparent() {
    byte[] traceId = new byte[16];
    byte[] spanId = new byte[8];
    RANDOM.nextBytes(traceId);
    RANDOM.nextBytes(spanId);
    traceId[0] |= 1;
    spanId[0] |= 1;
    HexFormat hex = HexFormat.of();
    return "00-" + hex.formatHex(traceId) + "-" + hex.formatHex(spanId) + "-01";
  }

  public record ContextExecutionOutcome(
      boolean success,
      ContextDecisionRecord record,
      ContextPolicyGuard.GuardResult guard,
      SubmitCanonicalExecutionUseCase.SubmitOutcome canonicalOutcome) {}
}
