package br.com.actionfinance.application.integration;

import java.util.Map;

public interface SpiderInteractionClient {

    SpiderLookupResult lookup(
            String correlationId,
            String idempotencyKey,
            String companyId,
            String titleId,
            String externalReference);

    default SpiderListResult list(
            String correlationId,
            String idempotencyKey,
            String companyId,
            String environment,
            String cursor,
            Integer limit) {
        return SpiderListResult.unavailable(correlationId, "Listagem não implementada neste cliente.");
    }

    record SpiderListResult(
            boolean available,
            String status,
            String decisionId,
            String requiredAction,
            String spiderPath,
            String capabilityId,
            String correlationId,
            String messageId,
            String environment,
            Integer itemCount,
            String nextCursor,
            java.util.List<java.util.Map<String, Object>> items,
            String errorCode,
            String errorMessage) {

        public static SpiderListResult unavailable(String correlationId, String message) {
            return new SpiderListResult(
                    false,
                    "UNAVAILABLE",
                    null,
                    "RETRY_LATER",
                    null,
                    null,
                    correlationId,
                    null,
                    null,
                    null,
                    null,
                    java.util.List.of(),
                    "SPIDER_UNAVAILABLE",
                    message);
        }
    }

    record SpiderLookupResult(
            boolean available,
            String status,
            String decisionId,
            String requiredAction,
            String spiderPath,
            String capabilityId,
            String correlationId,
            Map<String, Object> summary,
            String errorCode,
            String errorMessage) {

        public static SpiderLookupResult unavailable(String correlationId, String message) {
            return new SpiderLookupResult(
                    false,
                    "UNAVAILABLE",
                    null,
                    "RETRY_LATER",
                    null,
                    null,
                    correlationId,
                    Map.of(),
                    "SPIDER_UNAVAILABLE",
                    message);
        }
    }
}
