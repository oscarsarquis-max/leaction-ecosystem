package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionException;
import br.com.segsense.domain.demo.DemoProtectionJourney;
import br.com.segsense.application.urlcapture.UrlCaptureConfirmationRecord;
import br.com.segsense.application.urlcapture.UrlCaptureRecord;
import br.com.segsense.application.urlcapture.UrlCaptureRepository;
import br.com.segsense.application.urlcapture.UrlExtractedEnvelope;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SubmitDemoProtectionJourneyUseCase {

  public static final String SCENARIO = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  public static final String ALLOWED_OBJECTIVE = "UNDERSTAND_FAMILY_PROTECTION_OPTIONS";
  public static final String WATERMARK =
      "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO";
  public static final String WATERMARK_QUOTE =
      "SIMULAÇÃO DEMONSTRATIVA — SEM VALIDADE COMERCIAL — NÃO É OFERTA ICATU NEM CONTRATAÇÃO";

  private final DemoProtectionJourneyRepository journeys;
  private final DemoProtectionDecisionGateway gateway;
  private final DemoGovernedUrlSettings governedUrls;
  private final UrlCaptureRepository urlCaptures;

  public SubmitDemoProtectionJourneyUseCase(
      DemoProtectionJourneyRepository journeys,
      DemoProtectionDecisionGateway gateway,
      DemoGovernedUrlSettings governedUrls,
      UrlCaptureRepository urlCaptures) {
    this.journeys = journeys;
    this.gateway = gateway;
    this.governedUrls = governedUrls;
    this.urlCaptures = urlCaptures;
  }

  @Transactional
  public DemoProtectionJourney executeLegacy(String objective, String correlationId, String idempotencyKey) {
    if (objective == null || objective.isBlank()) {
      throw new DemoProtectionException("VALIDATION_ERROR", 400, "Declare um objetivo sintético.");
    }
    if (!ALLOWED_OBJECTIVE.equals(objective)) {
      throw new DemoProtectionException(
          "VALIDATION_ERROR",
          400,
          "A rota legado só aceita o objetivo sintético rotulado da prova HTTP anterior.");
    }
    if (idempotencyKey == null || idempotencyKey.isBlank()) {
      throw new DemoProtectionException("IDEMPOTENCY_KEY_REQUIRED", 400, "Idempotency-Key obrigatória.");
    }
    GovernedDemoSource family = GovernedDemoSourceRegistry.family();
    String fingerprint =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_LEGACY,
            objective,
            true,
            "",
            "",
            family.id(),
            family.version(),
            family.theme(),
            "",
            "SATELLITE_GOVERNED",
            "GOVERNED_SOURCE");
    return submitAssembled(
        AssembledContext.legacyGoverned(family),
        objective,
        correlationId,
        idempotencyKey,
        fingerprint,
        true);
  }

  @Transactional
  public DemoProtectionJourney execute(
      String objective,
      String correlationId,
      String idempotencyKey,
      String sourceUrl,
      String declaredContext,
      String contextChoice,
      boolean intentionConfirmed) {
    return execute(
        objective,
        correlationId,
        idempotencyKey,
        sourceUrl,
        declaredContext,
        contextChoice,
        intentionConfirmed,
        null,
        null,
        null,
        null);
  }

  @Transactional
  public DemoProtectionJourney execute(
      String objective,
      String correlationId,
      String idempotencyKey,
      String sourceUrl,
      String declaredContext,
      String contextChoice,
      boolean intentionConfirmed,
      String declaredIntention,
      String dwellingType,
      String insuredAmountCents,
      String coverPeriodMonths) {
    return execute(
        objective,
        correlationId,
        idempotencyKey,
        sourceUrl,
        declaredContext,
        contextChoice,
        intentionConfirmed,
        declaredIntention,
        dwellingType,
        insuredAmountCents,
        coverPeriodMonths,
        null);
  }

  @Transactional
  public DemoProtectionJourney execute(
      String objective,
      String correlationId,
      String idempotencyKey,
      String sourceUrl,
      String declaredContext,
      String contextChoice,
      boolean intentionConfirmed,
      String declaredIntention,
      String dwellingType,
      String insuredAmountCents,
      String coverPeriodMonths,
      String captureId) {
    if (idempotencyKey == null || idempotencyKey.isBlank()) {
      throw new DemoProtectionException("IDEMPOTENCY_KEY_REQUIRED", 400, "Idempotency-Key obrigatória.");
    }
    DemoPersonalDataGuard.rejectObviousPersonalData(declaredContext);
    DemoPersonalDataGuard.rejectObviousPersonalData(declaredIntention);
    DemoQuoteInputs.validateOptional(dwellingType, insuredAmountCents, coverPeriodMonths);
    String resolvedObjective = resolveObjective(objective, declaredIntention);
    if (resolvedObjective == null || resolvedObjective.isBlank()) {
      throw new DemoProtectionException("VALIDATION_ERROR", 400, "Declare o que você deseja fazer.");
    }
    AssembledContext assembled =
        assembleContext(sourceUrl, declaredContext, contextChoice, governedUrls.allowedPorts(), captureId);
    if (DemoIntentionClassifier.SIMULATE_HOME_QUOTE.equals(resolvedObjective) && assembled.status == null) {
      assembled = assembled.withQuoteInputs(dwellingType, insuredAmountCents, coverPeriodMonths);
    }
    String fingerprint =
        DemoJourneyRequestFingerprint.of(
            DemoJourneyRequestFingerprint.FLOW_PUBLIC,
            resolvedObjective,
            intentionConfirmed,
            contextChoice,
            assembled.referenceUrl,
            assembled.scenarioKey(),
            assembled.source == null ? "" : assembled.source.version(),
            assembled.declaredTheme,
            declaredContext,
            assembled.provenanceSourceType,
            assembled.contributionRoles(),
            dwellingType,
            insuredAmountCents,
            coverPeriodMonths,
            assembled.captureId == null ? "" : assembled.captureId,
            assembled.confirmationId == null ? "" : assembled.confirmationId,
            assembled.textSha256 == null ? "" : assembled.textSha256);
    return submitAssembled(
        assembled,
        resolvedObjective,
        correlationId,
        idempotencyKey,
        fingerprint,
        intentionConfirmed,
        declaredIntention);
  }

  static String resolveObjective(String objective, String declaredIntention) {
    if (hasText(objective)) {
      return objective.trim();
    }
    return DemoIntentionClassifier.code(declaredIntention);
  }

  private DemoProtectionJourney submitAssembled(
      AssembledContext assembled,
      String objective,
      String correlationId,
      String idempotencyKey,
      String fingerprint,
      boolean intentionConfirmed) {
    return submitAssembled(assembled, objective, correlationId, idempotencyKey, fingerprint, intentionConfirmed, null);
  }

  private DemoProtectionJourney submitAssembled(
      AssembledContext assembled,
      String objective,
      String correlationId,
      String idempotencyKey,
      String fingerprint,
      boolean intentionConfirmed,
      String declaredIntention) {
    String hash = DemoJourneyRequestFingerprint.sha256(idempotencyKey);
    var existing = journeys.findByIdempotencyKeyHash(hash);
    if (existing.isPresent()) {
      String stored = existing.get().requestFingerprint();
      if (stored == null || stored.isBlank() || !stored.equals(fingerprint)) {
        throw new DemoProtectionException(
            "IDEMPOTENCY_CONFLICT", 409, "A mesma chave já foi usada com outro pedido.");
      }
      return existing.get();
    }
    if (DemoIntentionClassifier.UNRECOGNIZED.equals(objective)) {
      return persistLocal(
          assembled,
          objective,
          correlationId,
          hash,
          fingerprint,
          "MISSING_CONTEXT",
          DemoIntentionClassifier.interpretation(objective),
          List.of("intention"));
    }
    if (DemoIntentionClassifier.EFFECTIVE_CONTRACT.equals(objective)) {
      return persistLocal(
          assembled,
          objective,
          correlationId,
          hash,
          fingerprint,
          "REJECTED",
          "Contratar de verdade depende de seguradora e produto autorizados. Esta fatia só calcula uma simulação.",
          List.of());
    }
    if (assembled.status == null && !intentionConfirmed) {
      throw new DemoProtectionException(
          "INTENTION_NOT_CONFIRMED", 400, "Confirme a intenção antes de enviar.");
    }
    if (assembled.status != null) {
      return persistLocal(assembled, objective, correlationId, hash, fingerprint);
    }
    Instant now = Instant.now();
    UUID id = UUID.randomUUID();
    String sourceTimestamp =
        assembled.provenanceSourceTimestamp != null
            ? assembled.provenanceSourceTimestamp
            : now.toString();
    DemoProtectionDecisionGateway.Result result =
        gateway.submit(
            new DemoProtectionDecisionGateway.Command(
                "segsense-demo-contract-v1",
                "SEGSENSE",
                assembled.scenarioKey(),
                objective,
                correlationId,
                idempotencyKey,
                assembled.headlineSourceId(),
                assembled.attributes,
                "USER_DECLARED",
                now,
                now,
                assembled.satelliteContractVersion,
                assembled.snapshotSchemaVersion,
                assembled.provenanceSourceType,
                assembled.provenanceCaptureMethod,
                assembled.provenanceTrustLevel,
                sourceTimestamp,
                assembled.contributions,
                assembled.selectedContribution));
    String status = mapStatus(result);
    String projection = projectionJson(id, objective, correlationId, result, assembled, now, now);
    DemoProtectionJourney journey =
        new DemoProtectionJourney(
            id,
            assembled.scenarioKey(),
            objective,
            status,
            correlationId,
            hash,
            result.decisionId(),
            result.mockResultId(),
            result.failureKind(),
            projection,
            now,
            now,
            fingerprint);
    return journeys.save(journey);
  }

  @Transactional(readOnly = true)
  public DemoProtectionJourney get(UUID id) {
    return journeys
        .findById(id)
        .orElseThrow(
            () -> new DemoProtectionException("NOT_FOUND", 404, "Jornada demonstrativa não encontrada."));
  }

  private static String mapStatus(DemoProtectionDecisionGateway.Result result) {
    if (!result.spiderReached()) {
      return "SPIDER_UNAVAILABLE";
    }
    if (CanonicalJourneyMapper.simulatedQuoteConfirmed(result)) {
      return "SIMULATED_QUOTE_AVAILABLE";
    }
    if (CanonicalJourneyMapper.preProposalConfirmed(result)) {
      return "PRE_PROPOSAL_AVAILABLE";
    }
    return switch (result.status()) {
      case "QUOTE_READY" -> "INCOMPLETE_CANONICAL";
      case "PRE_PROPOSAL_READY" -> "INCOMPLETE_CANONICAL";
      case "INCOMPLETE_CANONICAL" -> "INCOMPLETE_CANONICAL";
      case "REJECTED" -> "REJECTED";
      case "MOCK_UNAVAILABLE" -> "MOCK_UNAVAILABLE";
      case "MISSING_CONTEXT" -> "MISSING_CONTEXT";
      case "AMBIGUOUS" -> "AMBIGUOUS";
      case "NO_COMPATIBLE_CAPABILITY" -> "NO_COMPATIBLE_CAPABILITY";
      default -> "SPIDER_DECISION";
    };
  }

  private String projectionJson(
      UUID id,
      String objective,
      String correlationId,
      DemoProtectionDecisionGateway.Result result,
      AssembledContext assembled,
      Instant messageCreatedAt,
      Instant objectiveDeclaredAt) {
    Map<String, Object> projection = new LinkedHashMap<>();
    projection.put("id", id.toString());
    projection.put("watermark", result.watermark() == null ? WATERMARK : result.watermark());
    projection.put("notCommercial", true);
    projection.put("notIcatuProposal", true);
    projection.put("demoSliceOnly", true);
    projection.put("generatedAt", Instant.now().toString());
    projection.put("messageCreatedAt", messageCreatedAt.toString());
    projection.put("objectiveDeclaredAt", objectiveDeclaredAt.toString());
    if (assembled.editorialTimestamp() != null) {
      projection.put("editorialSourceTimestamp", assembled.editorialTimestamp());
    }
    projection.put("scenarioKey", assembled.scenarioKey());
    projection.put("declaredObjective", objective);
    projection.put("status", mapStatus(result));
    projection.put("correlationId", correlationId);
    projection.put("spiderDecisionId", result.decisionId());
    projection.put("decisionProvenance", result.decisionProvenance());
    projection.put("spiderPath", result.spiderPath());
    projection.put("satelliteId", "segsense");
    projection.put("satelliteRole", "EXPERIENCE");
    projection.put("satelliteContractVersion", result.contractVersion());
    boolean quote = CanonicalJourneyMapper.simulatedQuoteConfirmed(result);
    boolean illustrated = CanonicalJourneyMapper.preProposalConfirmed(result);
    if (quote) {
      projection.put("watermark", result.watermark() == null ? WATERMARK_QUOTE : result.watermark());
    }
    projection.put("intentionInterpretation", DemoIntentionClassifier.interpretation(objective));
    projection.put("capabilityId", (quote || illustrated) ? result.capabilityId() : null);
    projection.put("providerRequestId", (quote || illustrated) ? result.providerRequestId() : null);
    projection.put("requiredAction", result.requiredAction());
    projection.put("simulatedQuote", quote ? result.simulatedQuote() : null);
    projection.put("quoteReference", quote ? result.mockResultId() : null);
    projection.put("missingContext", result.missingContext() == null ? List.of() : result.missingContext());
    projection.put("missingQuestions", DemoMissingQuestions.fromCodes(result.missingContext()));
    projection.put(
        "originProvenance",
        result.originProvenance() == null ? Map.of() : result.originProvenance());
    projection.put("explanation", result.explanation());
    projection.put("mockCalled", result.mockCalled());
    projection.put("mockOrigin", result.mockOrigin());
    projection.put("providerId", result.providerId());
    projection.put("mockResultId", result.mockResultId());
    putContextBoard(projection, assembled);
    List<Map<String, Object>> items = new ArrayList<>();
    for (DemoProtectionDecisionGateway.Item item : result.items()) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("code", item.code());
      row.put("title", item.title());
      row.put("kind", item.kind());
      row.put("notOfferable", item.notOfferable());
      if (item.needAddressed() != null) {
        row.put("needAddressed", item.needAddressed());
      }
      if (item.pertinence() != null) {
        row.put("pertinence", item.pertinence());
      }
      if (item.limits() != null) {
        row.put("limits", item.limits());
      }
      items.add(row);
    }
    projection.put("items", items);
    projection.put("pendingForBroker", result.pendingForBroker());
    return DemoProjectionJson.write(projection);
  }

  private DemoProtectionJourney persistLocal(
      AssembledContext assembled,
      String objective,
      String correlationId,
      String hash,
      String fingerprint) {
    String explanation =
        "MISSING_CONTEXT".equals(assembled.status)
            ? "O contexto sintético não é suficiente. Indique continuidade familiar, interrupção de renda ou incêndios nas proximidades, ou use um link governado."
            : "Há conflito entre a fonte governada e o relato. Escolha qual conjunto de elementos usar; nada foi enviado à Spider.";
    List<String> missing =
        "MISSING_CONTEXT".equals(assembled.status) ? List.of("theme") : List.of();
    return persistLocal(
        assembled, objective, correlationId, hash, fingerprint, assembled.status, explanation, missing);
  }

  private DemoProtectionJourney persistLocal(
      AssembledContext assembled,
      String objective,
      String correlationId,
      String hash,
      String fingerprint,
      String status,
      String explanation,
      List<String> missingCodes) {
    Instant now = Instant.now();
    UUID id = UUID.randomUUID();
    Map<String, Object> projection = new LinkedHashMap<>();
    projection.put("id", id.toString());
    projection.put("watermark", WATERMARK);
    projection.put("notCommercial", true);
    projection.put("notIcatuProposal", true);
    projection.put("demoSliceOnly", true);
    projection.put("generatedAt", now.toString());
    projection.put("scenarioKey", assembled.scenarioKey());
    projection.put("declaredObjective", objective);
    projection.put("status", status);
    projection.put("correlationId", correlationId);
    projection.put("spiderDecisionId", null);
    projection.put("explanation", explanation);
    projection.put("intentionInterpretation", DemoIntentionClassifier.interpretation(objective));
    projection.put("mockCalled", false);
    projection.put("items", List.of());
    projection.put("pendingForBroker", List.of());
    projection.put("simulatedQuote", null);
    projection.put("missingContext", missingCodes);
    projection.put("missingQuestions", DemoMissingQuestions.fromCodes(missingCodes));
    putContextBoard(projection, assembled);
    DemoProtectionJourney journey =
        new DemoProtectionJourney(
            id,
            assembled.scenarioKey(),
            objective,
            status,
            correlationId,
            hash,
            null,
            null,
            "VALIDATION",
            DemoProjectionJson.write(projection),
            now,
            now,
            fingerprint);
    return journeys.save(journey);
  }

  private static void putContextBoard(Map<String, Object> projection, AssembledContext assembled) {
    projection.put("contextSourceTitle", assembled.source == null ? null : assembled.source.title());
    projection.put("contextSourceLabel", assembled.source == null ? null : assembled.source.sourceLabel());
    projection.put("contextSourceVersion", assembled.source == null ? null : assembled.source.version());
    projection.put("contextSourceUrl", assembled.referenceUrl);
    projection.put("declaredContextTheme", assembled.declaredTheme);
    projection.put("sourceTheme", assembled.source == null ? null : assembled.source.theme());
    projection.put("contextConflict", assembled.conflict);
    projection.put("contextElements", assembled.elements);
    projection.put("contextContributions", assembled.contributions);
    projection.put("selectedContribution", assembled.selectedContribution);
    projection.put("primarySourceType", assembled.provenanceSourceType);
  }

  static AssembledContext assembleContext(
      String sourceUrl, String declaredContext, String contextChoice, Set<Integer> allowedPorts) {
    return assembleGoverned(sourceUrl, declaredContext, contextChoice, allowedPorts);
  }

  AssembledContext assembleContext(
      String sourceUrl,
      String declaredContext,
      String contextChoice,
      Set<Integer> allowedPorts,
      String captureId) {
    if (hasText(captureId)) {
      return assembleCaptured(captureId);
    }
    return assembleGoverned(sourceUrl, declaredContext, contextChoice, allowedPorts);
  }

  static AssembledContext assembleGoverned(
      String sourceUrl, String declaredContext, String contextChoice, Set<Integer> allowedPorts) {
    boolean hasUrl = hasText(sourceUrl);
    boolean hasDeclared = hasText(declaredContext);
    if (!hasUrl && !hasDeclared) {
      return AssembledContext.blocked(
          "MISSING_CONTEXT",
          null,
          null,
          false,
          null,
          Map.of("declaredTheme", "", "note", "Nenhum contexto foi apresentado nesta solicitação."));
    }
    GovernedDemoSource fromUrl = null;
    String normalizedUrl = null;
    if (hasUrl) {
      DemoContextUrlGuard.Accepted accepted = DemoContextUrlGuard.accept(sourceUrl, allowedPorts);
      String slug = DemoContextUrlGuard.slugOf(accepted.path()).orElseThrow();
      fromUrl = GovernedDemoSourceRegistry.requireLive(slug);
      normalizedUrl = accepted.referenceUrl();
    }
    String declaredTheme = DemoDeclaredContextParser.themeFromDeclaredText(declaredContext);
    if (fromUrl == null) {
      if (declaredTheme == null) {
        return AssembledContext.blocked(
            "MISSING_CONTEXT",
            null,
            declaredTheme,
            false,
            null,
            Map.of("declaredTheme", "", "note", "O relato não mapeia o esquema limitado desta demo."));
      }
      if ("conflict".equals(declaredTheme)) {
        return AssembledContext.blocked(
            "AMBIGUOUS", null, declaredTheme, true, null, Map.of("declaredTheme", declaredTheme));
      }
      return AssembledContext.declaredOnly(declaredTheme);
    }
    boolean conflict =
        declaredTheme != null
            && !"conflict".equals(declaredTheme)
            && !declaredTheme.equals(fromUrl.theme());
    if ("conflict".equals(declaredTheme) || (conflict && !"source".equals(contextChoice))) {
      Map<String, Object> board = boardFrom(fromUrl, declaredTheme);
      board.put("conflict", true);
      return AssembledContext.blocked("AMBIGUOUS", fromUrl, declaredTheme, true, normalizedUrl, board);
    }
    if (declaredTheme == null) {
      return AssembledContext.governedOnly(fromUrl, normalizedUrl);
    }
    boolean choseSource = "source".equals(contextChoice);
    return AssembledContext.combination(fromUrl, declaredTheme, choseSource, conflict, normalizedUrl);
  }

  private AssembledContext assembleCaptured(String captureIdRaw) {
    UUID captureId;
    try {
      captureId = UUID.fromString(captureIdRaw.trim());
    } catch (IllegalArgumentException invalid) {
      throw new DemoProtectionException("VALIDATION_ERROR", 400, "Confirme o contexto extraído da URL antes de continuar.");
    }
    UrlCaptureRecord capture =
        urlCaptures
            .findCapture(captureId)
            .orElseThrow(
                () ->
                    new DemoProtectionException(
                        "VALIDATION_ERROR", 400, "Confirme o contexto extraído da URL antes de continuar."));
    if (!"FETCHED".equals(capture.resultCode())) {
      throw new DemoProtectionException(
          "VALIDATION_ERROR", 400, "Só é possível pedir possibilidades depois de obter e confirmar o conteúdo da URL.");
    }
    UrlCaptureConfirmationRecord confirmation =
        urlCaptures
            .findLatestConfirmation(captureId)
            .orElseThrow(
                () ->
                    new DemoProtectionException(
                        "VALIDATION_ERROR", 400, "Confirme o contexto extraído da URL antes de continuar."));
    List<Map<String, String>> confirmed = UrlExtractedEnvelope.readElementList(confirmation.confirmedElementsJson());
    List<Map<String, String>> corrections = UrlExtractedEnvelope.readElementList(confirmation.correctionsJson());
    List<Map<String, String>> supported =
        UrlExtractedEnvelope.supportedUrlExtracted(capture, confirmed);
    List<Map<String, Object>> contributions = new ArrayList<>();
    contributions.add(UrlExtractedEnvelope.urlContribution(capture, supported));
    boolean hasCorrection = corrections.stream().anyMatch(item -> "USER_DECLARED".equals(item.get("origin")));
    if (hasCorrection) {
      contributions.add(UrlExtractedEnvelope.correctionContribution(corrections));
    }
    String theme = firstElement(confirmed, "theme");
    Map<String, Object> board = new LinkedHashMap<>();
    board.put("origin", "URL_EXTRACTED");
    board.put("title", capture.title());
    board.put("finalHost", capture.finalHost());
    board.put("excerpt", capture.excerpt());
    board.put("theme", theme);
    Map<String, String> attributes = UrlExtractedEnvelope.attributes(confirmed);
    if (theme == null || theme.isBlank()) {
      attributes = new LinkedHashMap<>(attributes);
      attributes.put("constraint", "missing_context");
    }
    return new AssembledContext(
        theme == null || theme.isBlank() ? "MISSING_CONTEXT" : null,
        null,
        attributes,
        theme,
        false,
        capture.finalUrl() == null ? capture.requestedUrl() : capture.finalUrl(),
        board,
        contributions,
        hasCorrection ? "BOTH" : "URL_EXTRACTED",
        "1.2",
        "1.2",
        "URL_EXTRACTED",
        "SERVER_FETCH",
        "OBSERVED",
        capture.capturedAt() == null ? null : capture.capturedAt().toString(),
        capture.id().toString(),
        confirmation.id().toString(),
        capture.textSha256());
  }

  private static String firstElement(List<Map<String, String>> items, String key) {
    for (Map<String, String> item : items) {
      if (key.equals(item.get("key")) && item.get("value") != null && !item.get("value").isBlank()) {
        return item.get("value");
      }
    }
    return null;
  }

  private static Map<String, Object> boardFrom(GovernedDemoSource source, String declaredTheme) {
    Map<String, Object> board = new LinkedHashMap<>();
    if (source != null) {
      board.put("theme", source.theme());
      board.put("situation", source.situation());
      board.put("need", source.need());
      board.put("horizon", source.horizon());
      board.put("constraint", source.constraint());
      board.put("title", source.title());
      board.put("sourceLabel", source.sourceLabel());
      board.put("sourceVersion", source.version());
      board.put("authorizedExcerpt", source.authorizedExcerpt());
      board.put("origin", "GOVERNED_SOURCE");
      board.put("editorialCapturedAt", source.capturedAt());
    }
    if (declaredTheme != null) {
      board.put("declaredTheme", declaredTheme);
      board.put("declaredOrigin", "VISITOR_DECLARED");
    }
    return board;
  }

  private static boolean hasText(String value) {
    return value != null && !value.isBlank();
  }

  record AssembledContext(
      String status,
      GovernedDemoSource source,
      Map<String, String> attributes,
      String declaredTheme,
      boolean conflict,
      String referenceUrl,
      Map<String, Object> elements,
      List<Map<String, Object>> contributions,
      String selectedContribution,
      String satelliteContractVersion,
      String snapshotSchemaVersion,
      String provenanceSourceType,
      String provenanceCaptureMethod,
      String provenanceTrustLevel,
      String provenanceSourceTimestamp,
      String captureId,
      String confirmationId,
      String textSha256) {

    AssembledContext(
        String status,
        GovernedDemoSource source,
        Map<String, String> attributes,
        String declaredTheme,
        boolean conflict,
        String referenceUrl,
        Map<String, Object> elements,
        List<Map<String, Object>> contributions,
        String selectedContribution,
        String satelliteContractVersion,
        String snapshotSchemaVersion,
        String provenanceSourceType,
        String provenanceCaptureMethod,
        String provenanceTrustLevel,
        String provenanceSourceTimestamp) {
      this(
          status,
          source,
          attributes,
          declaredTheme,
          conflict,
          referenceUrl,
          elements,
          contributions,
          selectedContribution,
          satelliteContractVersion,
          snapshotSchemaVersion,
          provenanceSourceType,
          provenanceCaptureMethod,
          provenanceTrustLevel,
          provenanceSourceTimestamp,
          null,
          null,
          null);
    }

    static AssembledContext legacyGoverned(GovernedDemoSource source) {
      return new AssembledContext(
          null,
          source,
          source.attributes(),
          source.theme(),
          false,
          null,
          boardFrom(source, null),
          List.of(),
          null,
          "1.0",
          "1.0",
          "SATELLITE_GOVERNED",
          "SERVER_REGISTRY",
          "GOVERNED",
          source.capturedAt());
    }

    static AssembledContext declaredOnly(String declaredTheme) {
      Map<String, Object> board = new LinkedHashMap<>();
      board.put("declaredTheme", declaredTheme);
      board.put("declaredOrigin", "VISITOR_DECLARED");
      board.put("note", "O texto original não é enviado à Spider; só o tema estruturado.");
      return new AssembledContext(
          null,
          null,
          DemoDeclaredOrigin.attributes(declaredTheme),
          declaredTheme,
          false,
          null,
          board,
          List.of(DemoDeclaredOrigin.contribution(declaredTheme, true)),
          "VISITOR_DECLARED",
          "1.1",
          "1.1",
          "USER_DECLARED",
          "SATELLITE_DECLARED",
          "DECLARED",
          null);
    }

    static AssembledContext governedOnly(GovernedDemoSource source, String referenceUrl) {
      return new AssembledContext(
          null,
          source,
          compactGovernedAttributes(source),
          null,
          false,
          referenceUrl,
          boardFrom(source, null),
          List.of(DemoDeclaredOrigin.governedContribution(source, true)),
          "GOVERNED_SOURCE",
          "1.1",
          "1.1",
          "SATELLITE_GOVERNED",
          "SERVER_REGISTRY",
          "GOVERNED",
          source.capturedAt());
    }

    static AssembledContext combination(
        GovernedDemoSource source,
        String declaredTheme,
        boolean choseSource,
        boolean conflict,
        String referenceUrl) {
      boolean useDeclared = !choseSource;
      List<Map<String, Object>> contributions = new ArrayList<>();
      contributions.add(DemoDeclaredOrigin.governedContribution(source, true));
      contributions.add(DemoDeclaredOrigin.contribution(declaredTheme, useDeclared));
      String selected = choseSource ? "GOVERNED_SOURCE" : "BOTH";
      String headlineType = choseSource ? "SATELLITE_GOVERNED" : "USER_DECLARED";
      String capture = choseSource ? "SERVER_REGISTRY" : "SATELLITE_DECLARED";
      String trust = choseSource ? "GOVERNED" : "DECLARED";
      String timestamp = choseSource ? source.capturedAt() : null;
      return new AssembledContext(
          null,
          source,
          compactGovernedAttributes(source),
          declaredTheme,
          conflict,
          referenceUrl,
          boardFrom(source, declaredTheme),
          contributions,
          selected,
          "1.1",
          "1.1",
          headlineType,
          capture,
          trust,
          timestamp);
    }

    static AssembledContext blocked(
        String status,
        GovernedDemoSource source,
        String declaredTheme,
        boolean conflict,
        String referenceUrl,
        Map<String, Object> elements) {
      return new AssembledContext(
          status,
          source,
          Map.of(),
          declaredTheme,
          conflict,
          referenceUrl,
          elements,
          List.of(),
          null,
          "1.1",
          "1.1",
          source == null ? "USER_DECLARED" : "SATELLITE_GOVERNED",
          source == null ? "SATELLITE_DECLARED" : "SERVER_REGISTRY",
          source == null ? "DECLARED" : "GOVERNED",
          source == null ? null : source.capturedAt());
    }

    String scenarioKey() {
      if ("URL_EXTRACTED".equals(provenanceSourceType) && textSha256 != null) {
        return UrlExtractedEnvelope.sourceId(textSha256);
      }
      if ("VISITOR_DECLARED".equals(selectedContribution) && declaredTheme != null) {
        return DemoDeclaredOrigin.idForTheme(declaredTheme);
      }
      if (source != null) {
        return source.id();
      }
      return declaredTheme == null ? "" : DemoDeclaredOrigin.idForTheme(declaredTheme);
    }

    String headlineSourceId() {
      if ("URL_EXTRACTED".equals(provenanceSourceType) && textSha256 != null) {
        return UrlExtractedEnvelope.sourceId(textSha256);
      }
      if ("USER_DECLARED".equals(provenanceSourceType)) {
        return DemoDeclaredOrigin.idForTheme(declaredTheme);
      }
      return source == null ? scenarioKey() : source.id();
    }

    String contributionRoles() {
      List<String> roles = new ArrayList<>();
      for (Map<String, Object> contribution : contributions) {
        roles.add(String.valueOf(contribution.get("role")));
      }
      return String.join(",", roles);
    }

    String editorialTimestamp() {
      return source == null ? null : source.capturedAt();
    }

    AssembledContext withQuoteInputs(String dwellingType, String insuredAmountCents, String coverPeriodMonths) {
      Map<String, String> merged = new LinkedHashMap<>(attributes == null ? Map.of() : attributes);
      if (hasText(dwellingType)) {
        merged.put("dwellingType", dwellingType);
      }
      if (hasText(insuredAmountCents)) {
        merged.put("insuredAmountCents", insuredAmountCents);
      }
      if (hasText(coverPeriodMonths)) {
        merged.put("coverPeriodMonths", coverPeriodMonths);
      }
      if (merged.containsKey("dwellingType")
          && merged.containsKey("insuredAmountCents")
          && merged.containsKey("coverPeriodMonths")) {
        merged.put("ratingRuleVersion", "HOME_QUOTE_SYNTHETIC_V1");
      }
      return new AssembledContext(
          status,
          source,
          merged,
          declaredTheme,
          conflict,
          referenceUrl,
          elements,
          contributions,
          selectedContribution,
          satelliteContractVersion,
          snapshotSchemaVersion,
          provenanceSourceType,
          provenanceCaptureMethod,
          provenanceTrustLevel,
          provenanceSourceTimestamp,
          captureId,
          confirmationId,
          textSha256);
    }

    private static Map<String, String> compactGovernedAttributes(GovernedDemoSource source) {
      Map<String, String> attributes = new LinkedHashMap<>();
      attributes.put("channel", GovernedDemoOrigin.CHANNEL);
      attributes.put("purposeVersion", GovernedDemoOrigin.PURPOSE_VERSION);
      attributes.put("theme", source.theme());
      attributes.put("constraint", source.constraint());
      return attributes;
    }
  }
}
