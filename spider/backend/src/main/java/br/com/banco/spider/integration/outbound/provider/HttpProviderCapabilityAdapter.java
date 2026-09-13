package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

public final class HttpProviderCapabilityAdapter implements ProviderCapabilityPort {

  public static final String SECRET_HEADER = "X-SEGSENSE-Mock-Credential";

  private final WebClient.Builder builder;
  private final SatelliteRegistry registry;

  public HttpProviderCapabilityAdapter(WebClient.Builder builder, SatelliteRegistry registry) {
    this.builder = builder;
    this.registry = registry;
  }

  @Override
  public Mono<ExecutionResult> execute(ExecutionRequest request) {
    ProviderEntry provider = registry.resolveProvider(request.capabilityId());
    if (provider == null || provider.getSecret() == null || provider.getSecret().isBlank()) {
      return Mono.just(ExecutionResult.unavailable());
    }
    Duration timeout = provider.getTimeout() == null ? Duration.ofSeconds(3) : provider.getTimeout();
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", "1.0");
    payload.put("requestId", request.requestId());
    payload.put("correlationId", request.correlationId());
    payload.put("decisionId", request.decisionId());
    payload.put("capabilityId", request.capabilityId());
    payload.put("capabilityVersion", "1.0");
    payload.put("purpose", request.purpose());
    payload.put("inputs", Map.of("scenarioKey", request.scenarioKey() == null ? "" : request.scenarioKey()));
    payload.put("dataClassification", request.dataClassification());
    payload.put("requestedAt", Instant.parse("2026-09-13T12:00:00Z").toString());
    payload.put("callback", null);
    return builder
        .baseUrl(provider.getBaseUrl())
        .build()
        .post()
        .uri("/v1/provider/capabilities/{capabilityId}/executions", request.capabilityId())
        .contentType(MediaType.APPLICATION_JSON)
        .header(SECRET_HEADER, provider.getSecret())
        .header("X-Correlation-ID", request.correlationId())
        .bodyValue(payload)
        .retrieve()
        .bodyToMono(Map.class)
        .timeout(timeout)
        .map(body -> ok(request, body))
        .onErrorResume(WebClientResponseException.class, ignored -> Mono.just(ExecutionResult.unavailable()))
        .onErrorResume(ignored -> Mono.just(ExecutionResult.unavailable()));
  }

  private static ExecutionResult ok(ExecutionRequest request, Map<?, ?> body) {
    if (body == null || !"COMPLETED".equals(body.get("status"))) {
      return ExecutionResult.unavailable();
    }
    if (!"insurance-provider-mock".equals(body.get("providerId"))) {
      return ExecutionResult.unavailable();
    }
    Object resultNode = body.get("result");
    if (!(resultNode instanceof Map<?, ?> result)) {
      return ExecutionResult.unavailable();
    }
    if (!"ILLUSTRATIVE_NOT_ICATU_CONTRACT".equals(result.get("origin"))) {
      return ExecutionResult.unavailable();
    }
    List<ResultItem> items = new ArrayList<>();
    if (result.get("items") instanceof List<?> rawItems) {
      for (Object raw : rawItems) {
        if (raw instanceof Map<?, ?> item) {
          items.add(
              new ResultItem(
                  String.valueOf(item.get("code")),
                  String.valueOf(item.get("title")),
                  String.valueOf(item.get("kind")),
                  Boolean.TRUE.equals(item.get("notOfferable"))));
        }
      }
    }
    List<String> pending = new ArrayList<>();
    Object pendingNode = result.get("pendingForHumanReview");
    if (pendingNode instanceof List<?> rawPending) {
      for (Object raw : rawPending) {
        pending.add(String.valueOf(raw));
      }
    }
    return new ExecutionResult(
        true,
        "COMPLETED",
        request.requestId(),
        String.valueOf(body.get("providerId")),
        body.get("providerReference") == null ? null : String.valueOf(body.get("providerReference")),
        String.valueOf(result.get("origin")),
        result.get("watermark") == null ? null : String.valueOf(result.get("watermark")),
        items,
        pending);
  }
}
