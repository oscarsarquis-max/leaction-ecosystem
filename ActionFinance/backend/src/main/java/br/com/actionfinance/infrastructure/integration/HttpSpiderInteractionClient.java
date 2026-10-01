package br.com.actionfinance.infrastructure.integration;

import br.com.actionfinance.application.integration.SpiderInteractionClient;
import br.com.actionfinance.configuration.ActionFinanceProperties;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientException;

import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

@Component
public class HttpSpiderInteractionClient implements SpiderInteractionClient {

    private static final Logger log = LoggerFactory.getLogger(HttpSpiderInteractionClient.class);

    private final ActionFinanceProperties properties;
    private final RestClient restClient;

    public HttpSpiderInteractionClient(ActionFinanceProperties properties) {
        this.properties = properties;
        this.restClient = RestClient.builder().build();
    }

    @Override
    public SpiderLookupResult lookup(
            String correlationId,
            String idempotencyKey,
            String companyId,
            String titleId,
            String externalReference) {
        ActionFinanceProperties.Integration integration = properties.getIntegration();
        if (integration.getSpiderBaseUrl() == null || integration.getSpiderBaseUrl().isBlank()) {
            return SpiderLookupResult.unavailable(correlationId, "A Spider não está configurada neste ambiente.");
        }
        String now = Instant.now().truncatedTo(ChronoUnit.SECONDS).toString();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("contractVersion", "1.3");
        body.put("messageId", "afm-" + UUID.randomUUID());
        body.put("correlationId", correlationId);
        body.put("satelliteId", integration.getSatelliteId());
        body.put("satelliteRole", "EXPERIENCE");
        body.put("interactionType", "QUERY_STATUS");
        body.put("createdAt", now);
        body.put("idempotencyKey", idempotencyKey);
        body.put("purpose", "FINANCIAL_EXTERNAL_LOOKUP");
        body.put(
                "objective",
                Map.of("text", "LOOKUP_EXTERNAL_PAYMENT", "origin", "SATELLITE_GOVERNED", "declaredAt", now));
        body.put("dataClassification", "INTERNAL");
        body.put("responseChannel", "SYNC");
        body.put(
                "context",
                Map.of(
                        "snapshot",
                        Map.of(
                                "schemaVersion",
                                "1.3",
                                "classification",
                                "INTERNAL",
                                "nonPersonal",
                                true,
                                "provenance",
                                Map.of(
                                        "sourceType",
                                        "SATELLITE_GOVERNED",
                                        "sourceId",
                                        "ACTIONFINANCE_FINANCIAL_LOOKUP_V1",
                                        "sourceTimestamp",
                                        now,
                                        "captureMethod",
                                        "SERVER_REGISTRY",
                                        "trustLevel",
                                        "GOVERNED"),
                                "selectedContribution",
                                "GOVERNED_SOURCE",
                                "contributions",
                                List.of(
                                        Map.of(
                                                "role",
                                                "GOVERNED_SOURCE",
                                                "sourceType",
                                                "SATELLITE_GOVERNED",
                                                "sourceId",
                                                "ACTIONFINANCE_FINANCIAL_LOOKUP_V1",
                                                "sourceTimestamp",
                                                now,
                                                "captureMethod",
                                                "SERVER_REGISTRY",
                                                "trustLevel",
                                                "GOVERNED",
                                                "used",
                                                true,
                                                "elements",
                                                Map.of("theme", "payment_lookup"))),
                                "attributes",
                                Map.of(
                                        "channel",
                                        "ACTIONFINANCE_HOMOLOG",
                                        "purposeVersion",
                                        "financial-lookup-v1",
                                        "theme",
                                        "payment_lookup",
                                        "situation",
                                        "test_payment_follow_up",
                                        "need",
                                        "lookup_external_payment",
                                        "horizon",
                                        "days",
                                        "companyId",
                                        companyId))));
        Map<String, Object> lookup = new LinkedHashMap<>();
        lookup.put("companyId", companyId);
        lookup.put("externalReference", externalReference);
        lookup.put("originSystem", "ACTIONHUB_PAY");
        if (titleId != null && !titleId.isBlank()) {
            lookup.put("titleId", titleId);
        }
        body.put("extensions", Map.of("financialLookup", lookup));
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response =
                    restClient
                            .post()
                            .uri(trimSlash(integration.getSpiderBaseUrl()) + "/v1/satellites/interactions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .header("X-Spider-Satellite-Id", integration.getSatelliteId())
                            .header("X-Spider-Satellite-Secret", integration.getSpiderSecret())
                            .header("X-Correlation-ID", correlationId)
                            .header(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                            .body(body)
                            .retrieve()
                            .body(Map.class);
            if (response == null) {
                return SpiderLookupResult.unavailable(correlationId, "A Spider não devolveu resultado utilizável.");
            }
            Object summary = response.get("resultSummary");
            Map<String, Object> mapped =
                    summary instanceof Map<?, ?> map ? new LinkedHashMap<>((Map<String, Object>) map) : Map.of();
            return new SpiderLookupResult(
                    true,
                    text(response.get("status")),
                    text(response.get("decisionId")),
                    text(response.get("requiredAction")),
                    text(response.get("spiderPath")),
                    text(response.get("capabilityId")),
                    text(response.get("correlationId")),
                    mapped,
                    null,
                    null);
        } catch (RestClientException exception) {
            log.warn(
                    "spider lookup transport failed correlation={} type={} message={}",
                    correlationId,
                    exception.getClass().getSimpleName(),
                    exception.getMessage());
            return SpiderLookupResult.unavailable(
                    correlationId, "Não foi possível consultar a Spider. A pendência foi preservada.");
        }
    }

    @Override
    public SpiderListResult list(
            String correlationId,
            String idempotencyKey,
            String companyId,
            String environment,
            String cursor,
            Integer limit) {
        ActionFinanceProperties.Integration integration = properties.getIntegration();
        if (integration.getSpiderBaseUrl() == null || integration.getSpiderBaseUrl().isBlank()) {
            return SpiderListResult.unavailable(correlationId, "A Spider não está configurada neste ambiente.");
        }
        String now = Instant.now().truncatedTo(ChronoUnit.SECONDS).toString();
        String messageId = "afm-" + UUID.randomUUID();
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("contractVersion", "1.4");
        body.put("messageId", messageId);
        body.put("correlationId", correlationId);
        body.put("satelliteId", integration.getSatelliteId());
        body.put("satelliteRole", "EXPERIENCE");
        body.put("interactionType", "QUERY_STATUS");
        body.put("createdAt", now);
        body.put("idempotencyKey", idempotencyKey);
        body.put("purpose", "FINANCIAL_EXTERNAL_LIST");
        body.put(
                "objective",
                Map.of("text", "LIST_EXTERNAL_PAYMENTS", "origin", "SATELLITE_GOVERNED", "declaredAt", now));
        body.put("dataClassification", "INTERNAL");
        body.put("responseChannel", "SYNC");
        body.put(
                "context",
                Map.of(
                        "snapshot",
                        Map.of(
                                "schemaVersion",
                                "1.4",
                                "classification",
                                "INTERNAL",
                                "nonPersonal",
                                true,
                                "provenance",
                                Map.of(
                                        "sourceType",
                                        "SATELLITE_GOVERNED",
                                        "sourceId",
                                        "ACTIONFINANCE_FINANCIAL_LIST_V1",
                                        "sourceTimestamp",
                                        now,
                                        "captureMethod",
                                        "SERVER_REGISTRY",
                                        "trustLevel",
                                        "GOVERNED"),
                                "selectedContribution",
                                "GOVERNED_SOURCE",
                                "contributions",
                                List.of(
                                        Map.of(
                                                "role",
                                                "GOVERNED_SOURCE",
                                                "sourceType",
                                                "SATELLITE_GOVERNED",
                                                "sourceId",
                                                "ACTIONFINANCE_FINANCIAL_LIST_V1",
                                                "sourceTimestamp",
                                                now,
                                                "captureMethod",
                                                "SERVER_REGISTRY",
                                                "trustLevel",
                                                "GOVERNED",
                                                "used",
                                                true,
                                                "elements",
                                                Map.of("theme", "payment_list"))),
                                "attributes",
                                Map.of(
                                        "channel",
                                        "ACTIONFINANCE_HOMOLOG",
                                        "purposeVersion",
                                        "financial-list-v1",
                                        "theme",
                                        "payment_list",
                                        "situation",
                                        "test_payment_list",
                                        "need",
                                        "list_external_payments",
                                        "horizon",
                                        "days",
                                        "companyId",
                                        companyId))));
        Map<String, Object> list = new LinkedHashMap<>();
        list.put("companyId", companyId);
        list.put("originSystem", "ACTIONHUB_PAY");
        list.put("environment", environment);
        if (limit != null) {
            list.put("limit", limit);
        }
        if (cursor != null && !cursor.isBlank()) {
            list.put("cursor", cursor);
        }
        body.put("extensions", Map.of("financialList", list));
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> response =
                    restClient
                            .post()
                            .uri(trimSlash(integration.getSpiderBaseUrl()) + "/v1/satellites/interactions")
                            .contentType(MediaType.APPLICATION_JSON)
                            .header("X-Spider-Satellite-Id", integration.getSatelliteId())
                            .header("X-Spider-Satellite-Secret", integration.getSpiderSecret())
                            .header("X-Correlation-ID", correlationId)
                            .header(HttpHeaders.ACCEPT, MediaType.APPLICATION_JSON_VALUE)
                            .body(body)
                            .retrieve()
                            .body(Map.class);
            if (response == null) {
                return SpiderListResult.unavailable(correlationId, "A Spider não devolveu resultado utilizável.");
            }
            Object summary = response.get("resultSummary");
            Map<String, Object> mapped =
                    summary instanceof Map<?, ?> map ? new LinkedHashMap<>((Map<String, Object>) map) : Map.of();
            Object rawItems = mapped.get("items");
            List<Map<String, Object>> items = new ArrayList<>();
            if (rawItems instanceof List<?> listItems) {
                for (Object entry : listItems) {
                    if (entry instanceof Map<?, ?> row) {
                        items.add(new LinkedHashMap<>((Map<String, Object>) row));
                    }
                }
            }
            Integer itemCount = mapped.get("itemCount") instanceof Number n ? n.intValue() : items.size();
            String status = text(response.get("status"));
            boolean available = status == null || "READY".equals(status);
            return new SpiderListResult(
                    available,
                    status,
                    text(response.get("decisionId")),
                    text(response.get("requiredAction")),
                    text(response.get("spiderPath")),
                    text(response.get("capabilityId")),
                    text(response.get("correlationId")),
                    messageId,
                    text(mapped.get("environment")),
                    itemCount,
                    text(mapped.get("nextCursor")),
                    items,
                    available ? null : "SPIDER_UNAVAILABLE",
                    available ? null : "A Spider não devolveu a listagem.");
        } catch (RestClientException exception) {
            log.warn(
                    "spider list transport failed correlation={} type={} message={}",
                    correlationId,
                    exception.getClass().getSimpleName(),
                    exception.getMessage());
            return new SpiderListResult(
                    false,
                    "UNAVAILABLE",
                    null,
                    "RETRY_LATER",
                    null,
                    null,
                    correlationId,
                    messageId,
                    environment,
                    null,
                    null,
                    List.of(),
                    "SPIDER_UNAVAILABLE",
                    "Não foi possível consultar a Spider. Os itens já importados foram preservados.");
        }
    }

    private static String trimSlash(String value) {
        return value.endsWith("/") ? value.substring(0, value.length() - 1) : value;
    }

    private static String text(Object value) {
        return value == null ? null : String.valueOf(value);
    }
}
