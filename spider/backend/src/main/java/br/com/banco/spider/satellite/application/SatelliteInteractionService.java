package br.com.banco.spider.satellite.application;

import br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import reactor.core.publisher.Mono;

public final class SatelliteInteractionService {

  private final SatelliteRegistry registry;
  private final ProviderCapabilityPort providers;
  private final OperationalEventPublisher events;
  private final SatelliteIdempotencyStore store = new SatelliteIdempotencyStore();
  private final ConcurrentHashMap<String, SatelliteInteractionRequest.ContextSnapshot> contexts =
      new ConcurrentHashMap<>();

  public SatelliteInteractionService(
      SatelliteRegistry registry, ProviderCapabilityPort providers, OperationalEventPublisher events) {
    this.registry = registry;
    this.providers = providers;
    this.events = events;
  }

  public Mono<Outcome> interact(String authenticatedSatelliteId, SatelliteInteractionRequest request) {
    emit(OperationalEventType.SATELLITE_REQUEST_RECEIVED, request, OperationalEventOutcome.INFO, null);
    if (request == null) {
      return Mono.just(Outcome.invalid(400, "INVALID_PAYLOAD", "Pedido vazio.", null));
    }
    if (!SatelliteContractV1.supports(request.contractVersion())) {
      return Mono.just(
          Outcome.invalid(400, "INVALID_CONTRACT_VERSION", "Versão de contrato não suportada.", request.correlationId()));
    }
    SatelliteEntry entry = registry.requireExperience(authenticatedSatelliteId);
    if (entry == null) {
      return Mono.just(
          Outcome.invalid(403, "UNAUTHORIZED_SATELLITE", "Satélite não autorizado neste papel.", request.correlationId()));
    }
    if (request.satelliteId() == null || !authenticatedSatelliteId.equals(request.satelliteId())) {
      return Mono.just(
          Outcome.invalid(403, "UNAUTHORIZED_SATELLITE", "Identidade do envelope não confere.", request.correlationId()));
    }
    if (!"EXPERIENCE".equals(request.satelliteRole()) || !"EXPERIENCE".equals(entry.getRole())) {
      return Mono.just(
          Outcome.invalid(403, "UNAUTHORIZED_SATELLITE", "Papel não autorizado para este satélite.", request.correlationId()));
    }
    emit(OperationalEventType.SATELLITE_AUTHENTICATED, request, OperationalEventOutcome.SUCCESS, authenticatedSatelliteId);
    if (request.idempotencyKey() == null || request.idempotencyKey().isBlank()) {
      return Mono.just(
          Outcome.invalid(400, "INVALID_PAYLOAD", "idempotencyKey obrigatória.", request.correlationId()));
    }
    if (request.correlationId() == null || request.correlationId().isBlank()) {
      return Mono.just(
          Outcome.invalid(400, "INVALID_PAYLOAD", "correlationId obrigatório.", request.correlationId()));
    }
    if (!entry.getPurposes().contains(request.purpose())) {
      return Mono.just(
          Outcome.invalid(403, "UNAUTHORIZED_SATELLITE", "Finalidade não autorizada.", request.correlationId()));
    }
    if (!entry.getInteractionTypes().contains(request.interactionType())) {
      return Mono.just(
          Outcome.invalid(403, "UNAUTHORIZED_SATELLITE", "Interação não autorizada.", request.correlationId()));
    }
    if ("EXECUTE_CAPABILITY".equals(request.interactionType())
        || "CAPABILITY_RESULT".equals(request.interactionType())) {
      return Mono.just(
          Outcome.invalid(
              403, "UNAUTHORIZED_SATELLITE", "Experience Satellite não executa capability.", request.correlationId()));
    }
    String fingerprint = sha256(request.semanticFingerprint());
    SatelliteIdempotencyStore.Stored existing =
        store.get(authenticatedSatelliteId, request.idempotencyKey());
    if (existing != null) {
      if (!existing.sameBody(fingerprint)) {
        return Mono.just(
            Outcome.invalid(
                409, "IDEMPOTENCY_CONFLICT", "A mesma chave já foi usada com outro pedido.", request.correlationId()));
      }
      return Mono.just(Outcome.ok(existing.response()));
    }
    ContextCheck contextCheck = validateContext(entry, request);
    if (contextCheck.error != null) {
      return Mono.just(contextCheck.error);
    }
    emit(OperationalEventType.SATELLITE_CONTRACT_VALIDATED, request, OperationalEventOutcome.SUCCESS, null);
    emit(OperationalEventType.SATELLITE_CONTEXT_ACCEPTED, request, OperationalEventOutcome.SUCCESS, contextCheck.contextRef);
    if (request.objective() == null || request.objective().text() == null || request.objective().text().isBlank()) {
      return Mono.just(
          Outcome.invalid(400, "AMBIGUOUS_OBJECTIVE", "Objetivo ausente.", request.correlationId()));
    }
    emit(OperationalEventType.SATELLITE_OBJECTIVE_ACCEPTED, request, OperationalEventOutcome.SUCCESS, request.objective().text());
    if (!entry.getAllowedObjectives().contains(request.objective().text())) {
      Map<String, Object> rejected =
          response(
              request,
              "REJECTED",
              "spd-" + UUID.randomUUID(),
              "PRESENT_REJECTION",
              null,
              contextCheck.contextRef,
              "A Spider recusou a intenção confirmada: não está entre as permitidas nesta demonstração. Nenhum encaminhamento ao provedor foi feito.",
              List.of(),
              null);
      store.put(
          authenticatedSatelliteId,
          request.idempotencyKey(),
          new SatelliteIdempotencyStore.Stored(fingerprint, rejected));
      emit(OperationalEventType.SATELLITE_DECISION_CREATED, request, OperationalEventOutcome.REJECTED, "POLICY_REJECTED");
      emit(OperationalEventType.SATELLITE_RESPONSE_RETURNED, request, OperationalEventOutcome.SUCCESS, "REJECTED");
      return Mono.just(Outcome.ok(rejected));
    }
    DemoSliceRules.Decision slice = DemoSliceRules.evaluate(request);
    if ("MISSING_CONTEXT".equals(slice.status()) || "AMBIGUOUS".equals(slice.status())) {
      String requiredAction = "MISSING_CONTEXT".equals(slice.status()) ? "PROVIDE_CONTEXT" : "RESOLVE_AMBIGUITY";
      Map<String, Object> body =
          response(
              request,
              slice.status(),
              "spd-" + UUID.randomUUID(),
              requiredAction,
              null,
              contextCheck.contextRef,
              slice.explanation(),
              slice.missingContext(),
              null);
      store.put(
          authenticatedSatelliteId,
          request.idempotencyKey(),
          new SatelliteIdempotencyStore.Stored(fingerprint, body));
      emit(OperationalEventType.SATELLITE_DECISION_CREATED, request, OperationalEventOutcome.SUCCESS, slice.status());
      emit(OperationalEventType.SATELLITE_RESPONSE_RETURNED, request, OperationalEventOutcome.SUCCESS, slice.status());
      return Mono.just(Outcome.ok(body));
    }
    String capabilityId =
        slice.capabilityId() == null ? SatelliteContractV1.ILLUSTRATIVE_CAPABILITY : slice.capabilityId();
    if (registry.resolveProvider(capabilityId) == null) {
      return Mono.just(
          Outcome.invalid(
              400, "CAPABILITY_NOT_AVAILABLE", "Nenhum executor registrado para a capability.", request.correlationId()));
    }
    String decisionId = "spd-" + UUID.randomUUID();
    String requestId = "preq-" + UUID.randomUUID();
    String scenarioKey = slice.scenarioKey();
    Map<String, String> quoteInputs =
        SatelliteContractV1.HOME_QUOTE_CAPABILITY.equals(capabilityId)
            ? DemoSliceRules.quoteInputs(
                request.context() == null || request.context().snapshot() == null
                    ? Map.of()
                    : request.context().snapshot().attributes())
            : Map.of();
    emit(OperationalEventType.CAPABILITY_DISPATCHED, request, OperationalEventOutcome.INFO, capabilityId);
    return providers
        .execute(
            new ExecutionRequest(
                requestId,
                request.correlationId(),
                decisionId,
                capabilityId,
                request.purpose(),
                scenarioKey,
                request.dataClassification() == null ? "INTERNAL" : request.dataClassification(),
                quoteInputs))
        .map(
            result -> {
              emit(
                  OperationalEventType.PROVIDER_RESULT_RECEIVED,
                  request,
                  result.available() ? OperationalEventOutcome.SUCCESS : OperationalEventOutcome.FAILURE,
                  result.providerId());
              String status = result.available() ? "READY" : "PROVIDER_UNAVAILABLE";
              String requiredAction =
                  !result.available()
                      ? "RETRY_LATER"
                      : SatelliteContractV1.HOME_QUOTE_CAPABILITY.equals(capabilityId)
                          ? "PRESENT_SIMULATED_QUOTE"
                          : "PRESENT_ILLUSTRATIVE_PRE_PROPOSAL";
              Map<String, Object> body =
                  response(
                      request,
                      status,
                      decisionId,
                      requiredAction,
                      result.available() ? result : null,
                      contextCheck.contextRef,
                      result.available()
                          ? slice.explanation()
                          : "A Spider validou o satélite, mas o executor da capability não respondeu.",
                      List.of(),
                      result.available() ? capabilityId : null);
              store.put(
                  authenticatedSatelliteId,
                  request.idempotencyKey(),
                  new SatelliteIdempotencyStore.Stored(fingerprint, body));
              emit(OperationalEventType.SATELLITE_DECISION_CREATED, request, OperationalEventOutcome.SUCCESS, decisionId);
              emit(OperationalEventType.SATELLITE_RESPONSE_RETURNED, request, OperationalEventOutcome.SUCCESS, status);
              return Outcome.ok(body);
            });
  }

  private ContextCheck validateContext(SatelliteEntry entry, SatelliteInteractionRequest request) {
    if (request.context() == null) {
      return ContextCheck.error(
          Outcome.invalid(400, "MISSING_CONTEXT", "Contexto sintético ausente.", request.correlationId()));
    }
    if (request.context().contextRef() != null && request.context().snapshot() == null) {
      ContextSnapshot stored = contexts.get(request.context().contextRef());
      if (stored == null) {
        return ContextCheck.error(
            Outcome.invalid(400, "MISSING_CONTEXT", "contextRef desconhecido.", request.correlationId()));
      }
      String provenanceError = validateSnapshot(entry, stored, request.contractVersion());
      if (provenanceError != null) {
        return ContextCheck.error(
            Outcome.invalid(400, "INVALID_PAYLOAD", provenanceError, request.correlationId()));
      }
      return new ContextCheck(request.context().contextRef(), null);
    }
    ContextSnapshot snapshot = request.context().snapshot();
    if (snapshot == null) {
      return ContextCheck.error(
          Outcome.invalid(400, "MISSING_CONTEXT", "contextSnapshot ausente.", request.correlationId()));
    }
    String provenanceError = validateSnapshot(entry, snapshot, request.contractVersion());
    if (provenanceError != null) {
      return ContextCheck.error(
          Outcome.invalid(400, "INVALID_PAYLOAD", provenanceError, request.correlationId()));
    }
    String contextRef = "ctx-" + UUID.randomUUID();
    contexts.put(contextRef, snapshot);
    return new ContextCheck(contextRef, null);
  }

  private static String validateSnapshot(
      SatelliteEntry entry, ContextSnapshot snapshot, String contractVersion) {
    if (!snapshot.nonPersonal()) {
      return "O contexto desta interação precisa ser não pessoal.";
    }
    if (entry.getClassifications() != null
        && snapshot.classification() != null
        && !entry.getClassifications().contains(snapshot.classification())) {
      return "Classificação não autorizada para este satélite.";
    }
    if (SatelliteContractV1.is11(contractVersion)) {
      String contributionError = validateContributions(entry, snapshot);
      if (contributionError != null) {
        return contributionError;
      }
    } else {
      String governedError = validateGovernedHeadline(entry, snapshot.provenance());
      if (governedError != null) {
        return governedError;
      }
    }
    if (snapshot.attributes() != null && entry.getAllowedAttributes() != null) {
      for (Map.Entry<String, String> attribute : snapshot.attributes().entrySet()) {
        List<String> allowed = entry.getAllowedAttributes().get(attribute.getKey());
        if (allowed != null && !allowed.contains(attribute.getValue())) {
          return "Atributo de contexto não permitido.";
        }
      }
    }
    return null;
  }

  private static String validateContributions(SatelliteEntry entry, ContextSnapshot snapshot) {
    if (snapshot.contributions() == null || snapshot.contributions().isEmpty()) {
      return "Contribuições de proveniência obrigatórias no contrato 1.1.";
    }
    Provenance headline = snapshot.provenance();
    if (headline == null) {
      return "Provenance obrigatória.";
    }
    boolean headlineMatched = false;
    for (SatelliteInteractionRequest.Contribution contribution : snapshot.contributions()) {
      String error = validateContribution(entry, contribution);
      if (error != null) {
        return error;
      }
      if (headline.sourceType() != null
          && headline.sourceType().equals(contribution.sourceType())
          && headline.sourceId() != null
          && headline.sourceId().equals(contribution.sourceId())) {
        headlineMatched = true;
      }
    }
    if (!headlineMatched) {
      return "A proveniência principal precisa corresponder a uma contribuição identificável.";
    }
    return null;
  }

  private static String validateContribution(
      SatelliteEntry entry, SatelliteInteractionRequest.Contribution contribution) {
    if (contribution == null) {
      return "Contribuição inválida.";
    }
    if ("SATELLITE_GOVERNED".equals(contribution.sourceType())) {
      return validateGovernedHeadline(
          entry,
          new Provenance(
              contribution.sourceType(),
              contribution.sourceId(),
              contribution.sourceTimestamp(),
              contribution.captureMethod(),
              contribution.trustLevel()));
    }
    if ("USER_DECLARED".equals(contribution.sourceType())) {
      if (!"DECLARED".equals(contribution.trustLevel())) {
        return "Nível de confiança declarado insuficiente.";
      }
      if (!"SATELLITE_DECLARED".equals(contribution.captureMethod())) {
        return "Método de captura declarado inválido.";
      }
      if (entry.getDeclaredContextIds() == null
          || !entry.getDeclaredContextIds().contains(contribution.sourceId())) {
        return "Origem declarada não registrada para este satélite.";
      }
      return null;
    }
    return "Tipo de contribuição não autorizado nesta fatia.";
  }

  private static String validateGovernedHeadline(SatelliteEntry entry, Provenance provenance) {
    if (provenance == null) {
      return "Provenance obrigatória.";
    }
    if (!"SATELLITE_GOVERNED".equals(provenance.sourceType())) {
      return "Contexto de satélite EXPERIENCE deve ser SATELLITE_GOVERNED.";
    }
    if (!"GOVERNED".equals(provenance.trustLevel())) {
      return "Nível de confiança insuficiente.";
    }
    if (!"SERVER_REGISTRY".equals(provenance.captureMethod())) {
      return "Método de captura não governado.";
    }
    if (!entry.getGovernedContextIds().contains(provenance.sourceId())) {
      return "Origem contextual não registrada para este satélite.";
    }
    return null;
  }

  private Map<String, Object> response(
      SatelliteInteractionRequest request,
      String status,
      String decisionId,
      String requiredAction,
      ExecutionResult provider,
      String contextRef,
      String explanation,
      List<String> missingContext,
      String capabilityId) {
    Map<String, Object> body = new LinkedHashMap<>();
    body.put("contractVersion", request.contractVersion());
    body.put("decisionId", decisionId);
    body.put("status", status);
    body.put("requiredAction", requiredAction);
    body.put("resultSummary", provider == null ? null : provider.summary());
    body.put("missingContext", missingContext == null ? List.of() : missingContext);
    body.put("nextInteraction", null);
    body.put("correlationId", request.correlationId());
    body.put("contextRef", contextRef);
    body.put("explainabilityRef", "sat-exp-" + decisionId);
    body.put(
        "watermark",
        SatelliteContractV1.HOME_QUOTE_CAPABILITY.equals(capabilityId)
            ? SatelliteContractV1.WATERMARK_QUOTE
            : SatelliteContractV1.WATERMARK);
    body.put("explanation", explanation);
    body.put("originProvenance", request.provenanceMap());
    body.put(
        "spiderPath",
        SatelliteContractV1.is11(request.contractVersion())
            ? SatelliteContractV1.PATH_V1_1
            : SatelliteContractV1.PATH_V1);
    body.put("capabilityId", capabilityId);
    body.put("providerRequestId", provider == null ? null : provider.requestId());
    return body;
  }

  private void emit(
      OperationalEventType type,
      SatelliteInteractionRequest request,
      OperationalEventOutcome outcome,
      String reason) {
    if (events == null || request == null) {
      return;
    }
    OperationalEventAttributes.Builder attributes =
        OperationalEventAttributes.builder()
            .component("satellite-contract")
            .reasonCode(reason);
    attributes.put("satelliteId", request.satelliteId());
    attributes.put("role", request.satelliteRole());
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type,
            request.messageId(),
            request.correlationId(),
            "satellite-contract",
            outcome,
            null,
            attributes.build()));
  }

  private static String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }

  private record ContextCheck(String contextRef, Outcome error) {
    static ContextCheck error(Outcome outcome) {
      return new ContextCheck(null, outcome);
    }
  }

  public record Outcome(int status, String errorCode, String message, Map<String, Object> body) {
    static Outcome ok(Map<String, Object> body) {
      return new Outcome(200, null, null, body);
    }

    static Outcome invalid(int status, String code, String message, String correlationId) {
      Map<String, Object> error = new LinkedHashMap<>();
      error.put("errorCode", code);
      error.put("message", message);
      error.put("correlationId", correlationId);
      error.put("retryable", false);
      return new Outcome(status, code, message, error);
    }
  }
}
