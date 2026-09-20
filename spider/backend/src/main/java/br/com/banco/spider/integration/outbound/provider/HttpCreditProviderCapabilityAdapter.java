package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.SatelliteRegistry.ProviderBinding;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

public final class HttpCreditProviderCapabilityAdapter implements ProviderCapabilityPort {

  public static final String SECRET_HEADER = "X-Credit-Mock-Credential";
  public static final String PROVIDER_ID = "credit-provider-mock";
  public static final String SIMULATE = "SIMULATE_WORKING_CAPITAL";

  private final WebClient.Builder builder;
  private final SatelliteRegistry registry;

  public HttpCreditProviderCapabilityAdapter(WebClient.Builder builder, SatelliteRegistry registry) {
    this.builder = builder;
    this.registry = registry;
  }

  @Override
  public Mono<ExecutionResult> execute(ExecutionRequest request) {
    ProviderBinding binding = registry.resolveProviderBinding(request.capabilityId());
    if (binding == null || !PROVIDER_ID.equals(binding.providerId())) {
      return Mono.just(ExecutionResult.unavailable());
    }
    ProviderEntry provider = binding.entry();
    if (provider.getSecret() == null || provider.getSecret().isBlank()) {
      return Mono.just(ExecutionResult.unavailable());
    }
    Duration timeout = provider.getTimeout() == null ? Duration.ofSeconds(3) : provider.getTimeout();
    boolean simulate = SIMULATE.equals(request.capabilityId());
    Map<String, Object> inputs = request.capabilityInputs() == null ? Map.of() : request.capabilityInputs();
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", simulate ? "credit-mock/0.1" : "credit-mock/0.2");
    payload.put("requestId", request.requestId());
    payload.put("correlationId", request.correlationId());
    payload.put("decisionId", request.decisionId());
    payload.put("capabilityId", request.capabilityId());
    payload.put("capabilityVersion", "1.0");
    payload.put("purpose", simulate ? "WORKING_CAPITAL_SIMULATION" : "WORKING_CAPITAL_ASSESSMENT");
    payload.put("inputs", inputs);
    payload.put("dataClassification", request.dataClassification() == null ? "INTERNAL" : request.dataClassification());
    payload.put("requestedAt", Instant.now().truncatedTo(java.time.temporal.ChronoUnit.SECONDS).toString());
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

  @SuppressWarnings("unchecked")
  private static ExecutionResult ok(ExecutionRequest request, Map<?, ?> body) {
    if (body == null || !PROVIDER_ID.equals(body.get("providerId"))) {
      return ExecutionResult.unavailable();
    }
    if (!request.capabilityId().equals(String.valueOf(body.get("capabilityId")))) {
      return ExecutionResult.unavailable();
    }
    if (!request.requestId().equals(String.valueOf(body.get("requestId")))
        || !request.correlationId().equals(String.valueOf(body.get("correlationId")))) {
      return ExecutionResult.unavailable();
    }
    String status = String.valueOf(body.get("status"));
    if (!List.of("COMPLETED", "PENDING", "REJECTED").contains(status)) {
      return ExecutionResult.unavailable();
    }
    Object resultNode = body.get("result");
    if (!(resultNode instanceof Map<?, ?> result)) {
      return ExecutionResult.unavailable();
    }
    if (!Boolean.TRUE.equals(result.get("testDouble")) || Boolean.TRUE.equals(result.get("offerable"))) {
      return ExecutionResult.unavailable();
    }
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("kind", "CREDIT_STEP_RESULT");
    payload.put("capabilityId", request.capabilityId());
    payload.put("executorStatus", status);
    payload.put("reasonCodes", body.get("reasonCodes"));
    payload.put("result", result);
    payload.put("providerReference", body.get("providerReference"));
    payload.put("contractVersion", body.get("contractVersion"));
    return new ExecutionResult(
        true,
        status,
        request.requestId(),
        PROVIDER_ID,
        body.get("providerReference") == null ? null : String.valueOf(body.get("providerReference")),
        "NON_BINDING_DEMO",
        result.get("watermark") == null ? null : String.valueOf(result.get("watermark")),
        List.of(),
        List.of(),
        payload);
  }
}
