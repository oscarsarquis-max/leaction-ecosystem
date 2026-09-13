package br.com.segsense.application.demo;

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
      String idempotencyKey) {}

  record Item(String code, String title, String kind, boolean notOfferable) {}

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
      String requiredAction) {

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
          null);
    }
  }
}
