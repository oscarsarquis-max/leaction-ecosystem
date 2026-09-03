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
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.domain.BusinessIntentCatalog;
import br.com.banco.spider.context.domain.ContextGuardDecision;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.IntentRouteResolution;
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
import java.util.List;
import java.util.Map;
import java.util.Optional;
import reactor.core.publisher.Mono;

/** Orquestra o Context Plane sem criar atalho para a engine ou para autorização canônica. */
public final class ContextIntelligenceService {

  private static final SecureRandom RANDOM = new SecureRandom();

  private final BusinessIntentCatalog catalog;
  private final ContextPolicyGuard guard;
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
      DeterministicIntentRouter router,
      ContextDecisionStore store,
      SubmitCanonicalExecutionUseCase canonicalSubmit,
      OperationalEventPublisher events,
      IdentifierGenerator ids,
      SpiderClock clock,
      ObjectMapper mapper) {
    this.catalog = catalog;
    this.guard = guard;
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
    Instant createdAt = clock.now();
    var guardResult = guard.evaluate(contract, principalRef != null && !principalRef.isBlank());
    IntentRouteResolution route = router.resolve(contract, guardResult).orElse(null);
    String decisionId = ids.nextId("ctxd");
    ContextDecisionRecord record =
        new ContextDecisionRecord(
            decisionId,
            principalRef,
            contract,
            guardResult,
            route,
            createdAt,
            null,
            null,
            null,
            journey(contract, guardResult, route, createdAt));
    store.save(record);
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
    IntentRouteResolution route = router.resolve(contract, guardResult).orElse(null);
    if (!guardResult.accepted() || route == null) {
      return Mono.just(new ContextExecutionOutcome(false, preview.get(), guardResult, null));
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
    emitContextEvents(executionId, correlationId, contract, route, guardResult);
    CanonicalExecutionRequest canonical =
        canonicalRequest(executionId, correlationId, submittedAt, contract, route, originator);
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
      IntentContract contract,
      IntentRouteResolution route,
      AuthenticatedOriginator originator) {
    ObjectNode data = mapper.createObjectNode();
    data.put("mockScenario", route.mockScenario());
    data.put("contextDecision", "DETERMINISTIC");
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
      IntentRouteResolution route,
      ContextPolicyGuard.GuardResult guardResult) {
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
        OperationalEventType.ROUTE_RESOLVED,
        executionId,
        correlationId,
        OperationalEventAttributes.builder()
            .routeCode(route.routeRef())
            .put("capabilityRef", route.capabilityRef())
            .build());
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
      IntentRouteResolution route,
      Instant at) {
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
            "objective-selected",
            "Objetivo selecionado",
            "CONTEXT",
            "SUCCEEDED",
            "O objetivo "
                + contract.objective()
                + " foi selecionado no domínio "
                + contract.domain()
                + ".",
            at,
            Map.of("objective", contract.objective(), "domain", contract.domain()));
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
    if (route == null) {
      return List.of(objective, intent, policy);
    }
    ContextJourneyStage resolved =
        new ContextJourneyStage(
            "route-resolved",
            "Rota determinada",
            "CONTEXT",
            "SUCCEEDED",
            "O roteador determinístico associou a intenção "
                + contract.intent()
                + " à capability "
                + route.capabilityRef()
                + " e à rota "
                + route.routeRef()
                + ".",
            at,
            Map.of(
                "capabilityRef",
                route.capabilityRef(),
                "routeRef",
                route.routeRef(),
                "executionAvailability",
                route.executable() ? "CTX001_END_TO_END" : "PREVIEW_ONLY",
                "policyRef",
                route.policyRef()));
    return List.of(objective, intent, policy, resolved);
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
