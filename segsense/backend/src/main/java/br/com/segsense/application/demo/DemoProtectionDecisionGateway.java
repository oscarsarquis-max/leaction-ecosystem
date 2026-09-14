package br.com.segsense.application.demo;

import java.time.Instant;
import java.util.List;
import java.util.Map;

public interface DemoProtectionDecisionGateway {

  Result submit(Command command);

  record Command(
      String contractVersion,
      String applicationId,
      String scenarioKey,
      String declaredObjective,
      String correlationId,
      String idempotencyKey,
      String sourceId,
      Map<String, String> contextAttributes,
      String objectiveOrigin,
      Instant messageCreatedAt,
      Instant objectiveDeclaredAt,
      String satelliteContractVersion,
      String snapshotSchemaVersion,
      String provenanceSourceType,
      String provenanceCaptureMethod,
      String provenanceTrustLevel,
      String provenanceSourceTimestamp,
      List<Map<String, Object>> contributions,
      String selectedContribution) {

    public Command(
        String contractVersion,
        String applicationId,
        String scenarioKey,
        String declaredObjective,
        String correlationId,
        String idempotencyKey) {
      this(
          contractVersion,
          applicationId,
          scenarioKey,
          declaredObjective,
          correlationId,
          idempotencyKey,
          scenarioKey,
          Map.of(),
          "USER_DECLARED",
          Instant.now(),
          Instant.now(),
          "1.0",
          "1.0",
          "SATELLITE_GOVERNED",
          "SERVER_REGISTRY",
          "GOVERNED",
          GovernedDemoOrigin.CAPTURED_AT,
          List.of(),
          null);
    }

    public Command(
        String contractVersion,
        String applicationId,
        String scenarioKey,
        String declaredObjective,
        String correlationId,
        String idempotencyKey,
        String sourceId,
        Map<String, String> contextAttributes,
        String objectiveOrigin) {
      this(
          contractVersion,
          applicationId,
          scenarioKey,
          declaredObjective,
          correlationId,
          idempotencyKey,
          sourceId,
          contextAttributes,
          objectiveOrigin,
          Instant.now(),
          Instant.now(),
          "1.0",
          "1.0",
          "SATELLITE_GOVERNED",
          "SERVER_REGISTRY",
          "GOVERNED",
          GovernedDemoOrigin.CAPTURED_AT,
          List.of(),
          null);
    }
  }

  record Item(
      String code,
      String title,
      String kind,
      boolean notOfferable,
      String needAddressed,
      String pertinence,
      String limits) {

    public Item(String code, String title, String kind, boolean notOfferable) {
      this(code, title, kind, notOfferable, null, null, null);
    }
  }

  record Result(
      boolean spiderReached,
      String status,
      String decisionId,
      String explanation,
      String decisionProvenance,
      String watermark,
      boolean mockCalled,
      String mockResultId,
      String mockOrigin,
      String providerId,
      List<Item> items,
      List<String> pendingForBroker,
      Map<String, Object> originProvenance,
      String spiderPath,
      String failureKind,
      String contractVersion,
      String capabilityId,
      String providerRequestId,
      String requiredAction,
      Map<String, Object> simulatedQuote,
      List<String> missingContext) {

    public static Result spiderUnavailable() {
      return new Result(
          false,
          "SPIDER_UNAVAILABLE",
          null,
          "A Spider não respondeu.",
          null,
          null,
          false,
          null,
          null,
          null,
          List.of(),
          List.of(),
          Map.of(),
          null,
          "SPIDER",
          null,
          null,
          null,
          null,
          Map.of(),
          List.of());
    }
  }
}
