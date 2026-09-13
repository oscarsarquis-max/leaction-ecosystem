package br.com.segsense.application.demo;

import br.com.segsense.domain.demo.DemoProtectionException;
import br.com.segsense.domain.demo.DemoProtectionJourney;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class SubmitDemoProtectionJourneyUseCase {

  public static final String SCENARIO = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  public static final String ALLOWED_OBJECTIVE = "UNDERSTAND_FAMILY_PROTECTION_OPTIONS";
  public static final String WATERMARK =
      "DEMONSTRAÇÃO — SEM VALOR COMERCIAL — NÃO É COTAÇÃO/PROPOSTA DE CONTRATAÇÃO";

  private final DemoProtectionJourneyRepository journeys;
  private final DemoProtectionDecisionGateway gateway;

  public SubmitDemoProtectionJourneyUseCase(
      DemoProtectionJourneyRepository journeys, DemoProtectionDecisionGateway gateway) {
    this.journeys = journeys;
    this.gateway = gateway;
  }

  @Transactional
  public DemoProtectionJourney execute(String objective, String correlationId, String idempotencyKey) {
    if (objective == null || objective.isBlank()) {
      throw new DemoProtectionException("VALIDATION_ERROR", 400, "Declare um objetivo sintético.");
    }
    if (idempotencyKey == null || idempotencyKey.isBlank()) {
      throw new DemoProtectionException("IDEMPOTENCY_KEY_REQUIRED", 400, "Idempotency-Key obrigatória.");
    }
    String hash = sha256(idempotencyKey);
    var existing = journeys.findByIdempotencyKeyHash(hash);
    if (existing.isPresent()) {
      if (!existing.get().declaredObjective().equals(objective)) {
        throw new DemoProtectionException(
            "IDEMPOTENCY_CONFLICT", 409, "A mesma chave já foi usada com outro pedido.");
      }
      return existing.get();
    }
    Instant now = Instant.now();
    UUID id = UUID.randomUUID();
    DemoProtectionDecisionGateway.Result result =
        gateway.submit(
            new DemoProtectionDecisionGateway.Command(
                "segsense-demo-contract-v1",
                "SEGSENSE",
                SCENARIO,
                objective,
                correlationId,
                idempotencyKey));
    String status = mapStatus(result);
    String projection = projectionJson(id, objective, correlationId, result);
    DemoProtectionJourney journey =
        new DemoProtectionJourney(
            id,
            SCENARIO,
            objective,
            status,
            correlationId,
            hash,
            result.decisionId(),
            result.mockResultId(),
            result.failureKind(),
            projection,
            now,
            now);
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
    if (CanonicalJourneyMapper.preProposalConfirmed(result)) {
      return "PRE_PROPOSAL_AVAILABLE";
    }
    return switch (result.status()) {
      case "PRE_PROPOSAL_READY" -> "INCOMPLETE_CANONICAL";
      case "INCOMPLETE_CANONICAL" -> "INCOMPLETE_CANONICAL";
      case "REJECTED" -> "REJECTED";
      case "MOCK_UNAVAILABLE" -> "MOCK_UNAVAILABLE";
      default -> "SPIDER_DECISION";
    };
  }

  private String projectionJson(
      UUID id, String objective, String correlationId, DemoProtectionDecisionGateway.Result result) {
    Map<String, Object> projection = new LinkedHashMap<>();
    projection.put("id", id.toString());
    projection.put("watermark", result.watermark() == null ? WATERMARK : result.watermark());
    projection.put("notCommercial", true);
    projection.put("notIcatuProposal", true);
    projection.put("demoSliceOnly", true);
    projection.put("generatedAt", Instant.now().toString());
    projection.put("scenarioKey", SCENARIO);
    projection.put("declaredObjective", objective);
    projection.put("status", mapStatus(result));
    projection.put("correlationId", correlationId);
    projection.put("spiderDecisionId", result.decisionId());
    projection.put("decisionProvenance", result.decisionProvenance());
    projection.put("spiderPath", result.spiderPath());
    projection.put("satelliteId", "segsense");
    projection.put("satelliteRole", "EXPERIENCE");
    projection.put("satelliteContractVersion", result.contractVersion());
    projection.put("capabilityId", CanonicalJourneyMapper.preProposalConfirmed(result) ? result.capabilityId() : null);
    projection.put("providerRequestId", CanonicalJourneyMapper.preProposalConfirmed(result) ? result.providerRequestId() : null);
    projection.put("requiredAction", result.requiredAction());
    projection.put(
        "originProvenance",
        result.originProvenance() == null ? Map.of() : result.originProvenance());
    projection.put("explanation", result.explanation());
    projection.put("mockCalled", result.mockCalled());
    projection.put("mockOrigin", result.mockOrigin());
    projection.put("providerId", result.providerId());
    projection.put("mockResultId", result.mockResultId());
    List<Map<String, Object>> items = new ArrayList<>();
    for (DemoProtectionDecisionGateway.Item item : result.items()) {
      Map<String, Object> row = new LinkedHashMap<>();
      row.put("code", item.code());
      row.put("title", item.title());
      row.put("kind", item.kind());
      row.put("notOfferable", item.notOfferable());
      items.add(row);
    }
    projection.put("items", items);
    projection.put("pendingForBroker", result.pendingForBroker());
    return DemoProjectionJson.write(projection);
  }

  private static String sha256(String value) {
    try {
      return HexFormat.of()
          .formatHex(MessageDigest.getInstance("SHA-256").digest(value.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }
}
