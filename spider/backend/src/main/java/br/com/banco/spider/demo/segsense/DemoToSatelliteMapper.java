package br.com.banco.spider.demo.segsense;

import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Edge anti-corruption: demo DTO → Satellite Contract V1. Not Core. */
public final class DemoToSatelliteMapper {

  public static final String SATELLITE_ID = "segsense";

  private DemoToSatelliteMapper() {}

  public static SatelliteInteractionRequest toRequest(SegSenseDemoDecisionService.Command command) {
    if (command == null) {
      return null;
    }
    ContextBlock context = null;
    if (command.originSnapshot() != null) {
      SegSenseDemoOriginSnapshot origin = command.originSnapshot();
      Map<String, String> attributes = new LinkedHashMap<>();
      attributes.put("channel", origin.channel());
      attributes.put("editorialPieceVersion", origin.editorialPieceVersion());
      attributes.put("purposeVersion", origin.purposeVersion());
      context =
          new ContextBlock(
              null,
              new ContextSnapshot(
                  "1.0",
                  "INTERNAL",
                  origin.nonPersonal(),
                  new Provenance(
                      "SATELLITE_GOVERNED",
                      origin.editorialPieceKey(),
                      origin.capturedAt(),
                      "SERVER_REGISTRY",
                      "GOVERNED"),
                  attributes));
    }
    return new SatelliteInteractionRequest(
        SatelliteContractV1.VERSION,
        "msg-" + command.idempotencyKey(),
        command.correlationId(),
        SATELLITE_ID,
        "EXPERIENCE",
        "REQUEST_DECISION",
        SegSenseDemoOriginSnapshot.CAPTURED_AT,
        command.idempotencyKey(),
        SatelliteContractV1.PURPOSE_INSURANCE,
        new Objective(
            command.declaredObjective(), "SATELLITE_GOVERNED", SegSenseDemoOriginSnapshot.CAPTURED_AT),
        context,
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  @SuppressWarnings("unchecked")
  public static SegSenseDemoDecisionService.Decision toLegacy(
      br.com.banco.spider.satellite.application.SatelliteInteractionService.Outcome outcome) {
    if (outcome.status() != 200) {
      String code = outcome.errorCode();
      if ("IDEMPOTENCY_CONFLICT".equals(code)) {
        return SegSenseDemoDecisionService.Decision.conflict();
      }
      if ("MISSING_CONTEXT".equals(code) || "INVALID_PAYLOAD".equals(code) || "INVALID_CONTRACT_VERSION".equals(code)) {
        return SegSenseDemoDecisionService.Decision.invalid(outcome.message());
      }
      if ("UNAUTHENTICATED".equals(code)) {
        return new SegSenseDemoDecisionService.Decision(401, "AUTHENTICATION_REQUIRED", outcome.message(), null);
      }
      return SegSenseDemoDecisionService.Decision.invalid(outcome.message());
    }
    Map<String, Object> canonical = outcome.body();
    Map<String, Object> legacy = new LinkedHashMap<>();
    String status = String.valueOf(canonical.get("status"));
    String legacyStatus =
        switch (status) {
          case "READY" -> "PRE_PROPOSAL_READY";
          case "PROVIDER_UNAVAILABLE" -> "MOCK_UNAVAILABLE";
          default -> status;
        };
    legacy.put("contractVersion", SegSenseDemoDecisionService.CONTRACT_VERSION);
    legacy.put("notSatelliteContract", false);
    legacy.put("demoEndpointDeprecated", true);
    legacy.put("applicationId", "SEGSENSE");
    legacy.put("decisionId", canonical.get("decisionId"));
    legacy.put("status", legacyStatus);
    legacy.put("decisionProvenance", "SPIDER_SATELLITE_CONTRACT_V1");
    legacy.put("spiderPath", canonical.get("spiderPath"));
    Map<String, Object> provenance = new LinkedHashMap<>();
    if (canonical.get("originProvenance") instanceof Map<?, ?> origin) {
      provenance.putAll((Map<String, Object>) origin);
      if (origin.get("attributes") instanceof Map<?, ?> attributes) {
        Object channel = ((Map<?, ?>) attributes).get("channel");
        if (channel != null) {
          provenance.put("channel", channel);
        }
      }
      provenance.putIfAbsent("nonPersonal", true);
    }
    legacy.put("originProvenance", provenance);
    legacy.put("watermark", canonical.get("watermark"));
    legacy.put("correlationId", canonical.get("correlationId"));
    legacy.put("explanation", canonical.get("explanation"));
    Object summary = canonical.get("resultSummary");
    if (summary instanceof Map<?, ?> result && "READY".equals(status)) {
      legacy.put("mockCalled", true);
      Map<String, Object> mock = new LinkedHashMap<>();
      mock.put("providerId", result.get("providerId"));
      mock.put("origin", result.get("origin"));
      mock.put("resultId", result.get("providerReference"));
      mock.put("items", result.get("items") == null ? List.of() : result.get("items"));
      mock.put(
          "pendingForBroker",
          result.get("pendingForHumanReview") == null ? List.of() : result.get("pendingForHumanReview"));
      legacy.put("mock", mock);
    } else {
      legacy.put("mockCalled", false);
      legacy.put("mock", null);
    }
    return SegSenseDemoDecisionService.Decision.ok(legacy);
  }
}
