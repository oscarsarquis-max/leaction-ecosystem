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
      String dataClassification,
      Map<String, String> quoteInputs,
      Map<String, Object> capabilityInputs) {

    public ExecutionRequest(
        String requestId,
        String correlationId,
        String decisionId,
        String capabilityId,
        String purpose,
        String scenarioKey,
        String dataClassification,
        Map<String, String> quoteInputs) {
      this(
          requestId,
          correlationId,
          decisionId,
          capabilityId,
          purpose,
          scenarioKey,
          dataClassification,
          quoteInputs,
          Map.of());
    }

    public ExecutionRequest(
        String requestId,
        String correlationId,
        String decisionId,
        String capabilityId,
        String purpose,
        String scenarioKey,
        String dataClassification) {
      this(requestId, correlationId, decisionId, capabilityId, purpose, scenarioKey, dataClassification, Map.of());
    }
  }

  record ResultItem(
      String code,
      String title,
      String kind,
      boolean notOfferable,
      String needAddressed,
      String pertinence,
      String limits) {

    public ResultItem(String code, String title, String kind, boolean notOfferable) {
      this(code, title, kind, notOfferable, null, null, null);
    }
  }

  record ExecutionResult(
      boolean available,
      String status,
      String requestId,
      String providerId,
      String providerReference,
      String origin,
      String watermark,
      List<ResultItem> items,
      List<String> pendingForHumanReview,
      Map<String, Object> quote) {

    public ExecutionResult(
        boolean available,
        String status,
        String requestId,
        String providerId,
        String providerReference,
        String origin,
        String watermark,
        List<ResultItem> items,
        List<String> pendingForHumanReview) {
      this(
          available,
          status,
          requestId,
          providerId,
          providerReference,
          origin,
          watermark,
          items,
          pendingForHumanReview,
          Map.of());
    }

    public static ExecutionResult unavailable() {
      return new ExecutionResult(
          false, "FAILED", null, null, null, null, null, List.of(), List.of(), Map.of());
    }

    public Map<String, Object> summary() {
      Map<String, Object> summary = new java.util.LinkedHashMap<>();
      if (quote != null && !quote.isEmpty()) {
        summary.putAll(quote);
        summary.put("providerId", providerId);
        summary.put("providerReference", providerReference);
        summary.put("origin", origin);
        summary.put("testDouble", true);
        return summary;
      }
      summary.put("kind", "ILLUSTRATIVE_PROTECTION_SCENARIO");
      summary.put("providerId", providerId);
      summary.put("providerReference", providerReference);
      summary.put("origin", origin);
      summary.put("testDouble", true);
      java.util.List<Map<String, Object>> mapped = new java.util.ArrayList<>();
      for (ResultItem item : items) {
        Map<String, Object> row = new java.util.LinkedHashMap<>();
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
        mapped.add(row);
      }
      summary.put("items", mapped);
      summary.put("pendingForHumanReview", pendingForHumanReview);
      return summary;
    }
  }
}
