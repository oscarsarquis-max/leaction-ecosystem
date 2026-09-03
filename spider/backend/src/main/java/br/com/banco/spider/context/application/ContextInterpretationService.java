package br.com.banco.spider.context.application;

import br.com.banco.spider.config.ContextIntelligenceProperties;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.AllowedIntent;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderRequest;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderResult;
import br.com.banco.spider.context.application.port.ContextInterpretationProvider.ProviderStatus;
import br.com.banco.spider.context.application.port.InvalidContextInterpretationResponseException;
import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.contract.IntentProvenance;
import br.com.banco.spider.context.contract.IntentProvenanceSource;
import br.com.banco.spider.context.domain.BusinessIntentCatalog;
import br.com.banco.spider.context.domain.BusinessIntentDefinition;
import br.com.banco.spider.context.domain.ContextGuardDecision;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import reactor.core.publisher.Mono;

/** Converte saída probabilística validada no mesmo pipeline determinístico CTX-001. */
public final class ContextInterpretationService {

  private final ContextIntelligenceProperties properties;
  private final ContextInterpretationProvider provider;
  private final ContextInterpreterPrompt prompt;
  private final ContextInputRedactor redactor;
  private final BusinessIntentCatalog catalog;
  private final ContextIntelligenceService context;
  private final OperationalEventPublisher events;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;

  public ContextInterpretationService(
      ContextIntelligenceProperties properties,
      ContextInterpretationProvider provider,
      ContextInterpreterPrompt prompt,
      ContextInputRedactor redactor,
      BusinessIntentCatalog catalog,
      ContextIntelligenceService context,
      OperationalEventPublisher events,
      IdentifierGenerator ids,
      SpiderClock clock) {
    this.properties = properties;
    this.provider = provider;
    this.prompt = prompt;
    this.redactor = redactor;
    this.catalog = catalog;
    this.context = context;
    this.events = events;
    this.ids = ids;
    this.clock = clock;
  }

  public AiState state() {
    if (!properties.getAi().isEnabled()) return AiState.DISABLED;
    return provider == null ? AiState.UNAVAILABLE : AiState.ACTIVE;
  }

  public String providerId() {
    return provider == null ? null : provider.providerId();
  }

  public Mono<InterpretationResult> interpret(String objectiveText, String principalRef) {
    if (!properties.getAi().isEnabled()) {
      return Mono.just(
          InterpretationResult.failed(
              InterpretationStatus.DISABLED,
              AiState.DISABLED,
              "A interpretação contextual por IA está desabilitada."));
    }
    if (provider == null) {
      return Mono.just(
          InterpretationResult.failed(
              InterpretationStatus.PROVIDER_UNAVAILABLE,
              AiState.UNAVAILABLE,
              "Não foi possível interpretar este objetivo com segurança."));
    }

    ContextInputRedactor.RedactionResult redacted = redactor.redact(objectiveText);
    if (redacted.safeObjective().isBlank()) {
      return Mono.just(
          InterpretationResult.failed(
              InterpretationStatus.INVALID_INPUT,
              AiState.ACTIVE,
              "Descreva uma situação ou objetivo antes de interpretar."));
    }
    String interpretationId = ids.nextId("ctxi");
    Instant requestedAt = clock.now();
    publish(
        OperationalEventType.AI_INTERPRETATION_REQUESTED,
        interpretationId,
        OperationalEventOutcome.INFO,
        "AI_INTERPRETATION_REQUESTED",
        null,
        redacted.redactedFieldsCount());

    ProviderRequest request =
        new ProviderRequest(
            redacted.safeObjective(),
            prompt.version(),
            "1.0",
            catalog.list().stream().map(ContextInterpretationService::allowedIntent).toList());

    return provider
        .interpret(request)
        .timeout(properties.getAi().getTimeout())
        .map(
            result ->
                process(
                    interpretationId,
                    requestedAt,
                    redacted,
                    principalRef,
                    validateProviderResult(result)))
        .onErrorResume(
            TimeoutException.class,
            error ->
                Mono.just(
                    failed(
                        interpretationId,
                        redacted,
                        InterpretationStatus.TIMEOUT,
                        "AI_INTERPRETATION_TIMEOUT")))
        .onErrorResume(
            InvalidContextInterpretationResponseException.class,
            error ->
                Mono.just(
                    failed(
                        interpretationId,
                        redacted,
                        InterpretationStatus.INVALID_RESPONSE,
                        "AI_INTERPRETATION_INVALID_RESPONSE")))
        .onErrorResume(
            error ->
                Mono.just(
                    failed(
                        interpretationId,
                        redacted,
                        InterpretationStatus.PROVIDER_UNAVAILABLE,
                        "AI_INTERPRETATION_PROVIDER_UNAVAILABLE")));
  }

  private InterpretationResult process(
      String interpretationId,
      Instant requestedAt,
      ContextInputRedactor.RedactionResult redacted,
      String principalRef,
      ProviderResult providerResult) {
    if (providerResult.status() == ProviderStatus.AMBIGUOUS) {
      List<String> candidates =
          providerResult.candidateIntents().stream()
              .filter(intent -> catalog.findByIntent(intent).isPresent())
              .distinct()
              .toList();
      ContextInterpretationEvidence evidence =
          evidence(
              interpretationId,
              requestedAt,
              redacted,
              providerResult,
              null,
              List.of(),
              candidates);
      publish(
          OperationalEventType.AI_INTERPRETATION_REJECTED,
          interpretationId,
          OperationalEventOutcome.REJECTED,
          "AMBIGUOUS",
          providerResult,
          redacted.redactedFieldsCount());
      return new InterpretationResult(
          InterpretationStatus.AMBIGUOUS,
          AiState.ACTIVE,
          "Preciso entender melhor o objetivo.",
          redacted.safeObjective(),
          null,
          evidence);
    }
    if (providerResult.status() == ProviderStatus.UNSUPPORTED_INTENT) {
      publish(
          OperationalEventType.AI_INTERPRETATION_REJECTED,
          interpretationId,
          OperationalEventOutcome.REJECTED,
          "UNSUPPORTED_INTENT",
          providerResult,
          redacted.redactedFieldsCount());
      return new InterpretationResult(
          InterpretationStatus.UNSUPPORTED_INTENT,
          AiState.ACTIVE,
          "Este objetivo não corresponde às situações disponíveis no Spider.",
          redacted.safeObjective(),
          null,
          evidence(
              interpretationId,
              requestedAt,
              redacted,
              providerResult,
              null,
              List.of(),
              List.of()));
    }

    BusinessIntentDefinition definition =
        catalog
            .findByIntent(providerResult.intent())
            .orElseThrow(
                () ->
                    new InvalidContextInterpretationResponseException(
                        "PROVIDER_INTENT_NOT_IN_CATALOG"));
    validateEntityVocabulary(definition, providerResult.entities());
    List<String> missing =
        definition.requiredEntityKeys().stream()
            .filter(key -> blank(providerResult.entities().get(key)))
            .sorted()
            .toList();
    ContextInterpretationEvidence evidence =
        evidence(
            interpretationId,
            requestedAt,
            redacted,
            providerResult,
            definition,
            missing,
            List.of());
    IntentContract contract =
        new IntentContract(
            "1.0",
            definition.intent(),
            definition.domain(),
            definition.objective(),
            providerResult.entities(),
            IntentConstraints.readOnlyWithConfirmation(),
            new IntentProvenance(
                IntentProvenanceSource.NATURAL_LANGUAGE, "context-ai:" + interpretationId),
            providerResult.confidence());
    ContextDecisionRecord decision = context.resolve(contract, principalRef, evidence);
    InterpretationStatus status = statusFrom(decision.guard().decision());
    publish(
        OperationalEventType.AI_INTERPRETATION_SUCCEEDED,
        interpretationId,
        OperationalEventOutcome.SUCCESS,
        status.name(),
        providerResult,
        redacted.redactedFieldsCount());
    return new InterpretationResult(
        status,
        AiState.ACTIVE,
        messageFor(status),
        redacted.safeObjective(),
        decision,
        evidence);
  }

  private ProviderResult validateProviderResult(ProviderResult result) {
    if (result == null || result.status() == null || result.confidence() == null) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_RESULT_INCOMPLETE");
    }
    BigDecimal confidence = result.confidence();
    if (confidence.compareTo(BigDecimal.ZERO) < 0 || confidence.compareTo(BigDecimal.ONE) > 0) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_CONFIDENCE_OUT_OF_RANGE");
    }
    if (result.status() == ProviderStatus.MATCHED && blank(result.intent())) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_MATCHED_INTENT_MISSING");
    }
    if (result.status() == ProviderStatus.MATCHED && !result.candidateIntents().isEmpty()) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_MATCHED_CANDIDATES_NOT_ALLOWED");
    }
    if (result.status() != ProviderStatus.MATCHED
        && (!blank(result.intent()) || !result.entities().isEmpty())) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_NON_MATCHED_PAYLOAD_INVALID");
    }
    if (result.candidateIntents().stream()
        .anyMatch(intent -> catalog.findByIntent(intent).isEmpty())) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_CANDIDATE_NOT_IN_CATALOG");
    }
    return result;
  }

  private static void validateEntityVocabulary(
      BusinessIntentDefinition definition, Map<String, String> entities) {
    boolean invalidKey =
        entities.keySet().stream().anyMatch(key -> !definition.requiredEntityKeys().contains(key));
    boolean blankValue = entities.values().stream().anyMatch(ContextInterpretationService::blank);
    if (invalidKey || blankValue) {
      throw new InvalidContextInterpretationResponseException(
          "PROVIDER_ENTITY_NOT_ALLOWED");
    }
  }

  private ContextInterpretationEvidence evidence(
      String interpretationId,
      Instant requestedAt,
      ContextInputRedactor.RedactionResult redacted,
      ProviderResult result,
      BusinessIntentDefinition definition,
      List<String> missing,
      List<String> candidates) {
    return new ContextInterpretationEvidence(
        interpretationId,
        redacted.safeObjective(),
        provider.providerId(),
        provider.modelId(),
        requestedAt,
        prompt.version(),
        "1.0",
        definition == null ? result.intent() : definition.intent(),
        definition == null ? null : definition.domain(),
        result.entities(),
        missing,
        candidates,
        result.confidence(),
        result.usage(),
        result.latencyMs(),
        redacted.redactedFieldsCount());
  }

  private InterpretationResult failed(
      String interpretationId,
      ContextInputRedactor.RedactionResult redacted,
      InterpretationStatus status,
      String reasonCode) {
    publish(
        OperationalEventType.AI_INTERPRETATION_FAILED,
        interpretationId,
        OperationalEventOutcome.FAILURE,
        reasonCode,
        null,
        redacted.redactedFieldsCount());
    return new InterpretationResult(
        status,
        AiState.UNAVAILABLE,
        "Não foi possível interpretar este objetivo com segurança.",
        redacted.safeObjective(),
        null,
        null);
  }

  private void publish(
      OperationalEventType type,
      String interpretationId,
      OperationalEventOutcome outcome,
      String reasonCode,
      ProviderResult result,
      int redactedFieldsCount) {
    OperationalEventAttributes.Builder attributes =
        OperationalEventAttributes.builder()
            .reasonCode(reasonCode)
            .put("provider", provider == null ? null : provider.providerId())
            .put("model", provider == null ? null : provider.modelId())
            .put("redactedFields", Integer.toString(redactedFieldsCount));
    if (result != null) {
      attributes
          .put("interpretationStatus", result.status().name())
          .put("latencyMs", Long.toString(result.latencyMs()))
          .put(
              "inputTokens",
              result.usage().inputTokens() == null
                  ? null
                  : result.usage().inputTokens().toString())
          .put(
              "outputTokens",
              result.usage().outputTokens() == null
                  ? null
                  : result.usage().outputTokens().toString())
          .put(
              "totalTokens",
              result.usage().totalTokens() == null
                  ? null
                  : result.usage().totalTokens().toString());
    }
    OperationalEventEmit.publish(
        events,
        OperationalEventEmit.draft(
            type,
            interpretationId,
            interpretationId,
            "context-ai-interpreter",
            outcome,
            null,
            attributes.build()));
  }

  private static AllowedIntent allowedIntent(BusinessIntentDefinition definition) {
    return new AllowedIntent(
        definition.intent(),
        definition.domain(),
        definition.objective(),
        definition.requiredEntityKeys().stream().sorted().toList());
  }

  private static InterpretationStatus statusFrom(ContextGuardDecision decision) {
    return switch (decision) {
      case ACCEPTED -> InterpretationStatus.SUCCEEDED;
      case MISSING_CONTEXT -> InterpretationStatus.MISSING_CONTEXT;
      case AMBIGUOUS -> InterpretationStatus.AMBIGUOUS;
      case UNSUPPORTED_INTENT -> InterpretationStatus.UNSUPPORTED_INTENT;
      default -> InterpretationStatus.REJECTED;
    };
  }

  private static String messageFor(InterpretationStatus status) {
    return switch (status) {
      case SUCCEEDED -> "Objetivo interpretado. Revise a intenção antes de executar.";
      case MISSING_CONTEXT -> "Falta uma informação para continuar com segurança.";
      case AMBIGUOUS -> "Preciso entender melhor o objetivo.";
      default -> "Não foi possível interpretar este objetivo com segurança.";
    };
  }

  private static boolean blank(String value) {
    return value == null || value.isBlank();
  }

  public enum AiState {
    ACTIVE,
    DISABLED,
    UNAVAILABLE
  }

  public enum InterpretationStatus {
    SUCCEEDED,
    MISSING_CONTEXT,
    AMBIGUOUS,
    UNSUPPORTED_INTENT,
    REJECTED,
    INVALID_INPUT,
    INVALID_RESPONSE,
    TIMEOUT,
    PROVIDER_UNAVAILABLE,
    DISABLED
  }

  public record InterpretationResult(
      InterpretationStatus status,
      AiState aiState,
      String message,
      String requestedObjective,
      ContextDecisionRecord decision,
      ContextInterpretationEvidence interpretation) {

    static InterpretationResult failed(
        InterpretationStatus status, AiState aiState, String message) {
      return new InterpretationResult(status, aiState, message, null, null, null);
    }
  }
}
