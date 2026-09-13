package br.com.banco.spider.satellite.application.port;

import java.util.List;
import java.util.Map;
import reactor.core.publisher.Mono;

public interface ProviderCapabilityPort {

  Mono<ExecutionResult> execute(ExecutionRequest request);

  record ExecutionRequest(
      String requestId,
      String correlationId,
      String decisionId,
      String capabilityId,
      String purpose,
      String scenarioKey,
      String dataClassification) {}

  record ResultItem(String code, String title, String kind, boolean notOfferable) {}

  record ExecutionResult(
      boolean available,
      String status,
      String requestId,
      String providerId,
      String providerReference,
      String origin,
      String watermark,
      List<ResultItem> items,
      List<String> pendingForHumanReview) {

    public static ExecutionResult unavailable() {
      return new ExecutionResult(
          false, "FAILED", null, null, null, null, null, List.of(), List.of());
    }

    public Map<String, Object> summary() {
      Map<String, Object> summary = new java.util.LinkedHashMap<>();
      summary.put("kind", "ILLUSTRATIVE_PROTECTION_SCENARIO");
      summary.put("providerId", providerId);
      summary.put("providerReference", providerReference);
      summary.put("origin", origin);
      summary.put("testDouble", true);
      summary.put("items", items);
      summary.put("pendingForHumanReview", pendingForHumanReview);
      return summary;
    }
  }
}
