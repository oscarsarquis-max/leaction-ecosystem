package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.application.BibliotecaStateProjection;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.Exceptions;
import reactor.core.publisher.Mono;

public final class HttpActionHubBibliotecaCapabilityAdapter implements ProviderCapabilityPort {

  public static final String PROVIDER_ID = "actionhub-biblioteca";
  public static final String SECRET_HEADER = "X-ActionHub-Biblioteca-Credential";

  private final WebClient.Builder builder;
  private final SatelliteRegistry registry;

  public HttpActionHubBibliotecaCapabilityAdapter(WebClient.Builder builder, SatelliteRegistry registry) {
    this.builder = builder;
    this.registry = registry;
  }

  @Override
  public Mono<ExecutionResult> execute(ExecutionRequest request) {
    ProviderEntry provider = registry.resolveProvider(request.capabilityId());
    if (provider == null || provider.getSecret() == null || provider.getSecret().isBlank()) {
      return Mono.just(ExecutionResult.unavailable());
    }
    if (!SatelliteContractV1.isBibliotecaCapability(request.capabilityId())) {
      return Mono.just(ExecutionResult.unavailable());
    }
    Duration timeout = provider.getTimeout() == null ? Duration.ofSeconds(8) : provider.getTimeout();
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", SatelliteContractV1.VERSION_1_5);
    payload.put("requestId", request.requestId());
    payload.put("correlationId", request.correlationId());
    payload.put("decisionId", request.decisionId());
    payload.put("capabilityId", request.capabilityId());
    payload.put("capabilityVersion", "1.0");
    payload.put("purpose", request.purpose());
    payload.put("inputs", request.capabilityInputs() == null ? Map.of() : request.capabilityInputs());
    payload.put("dataClassification", request.dataClassification());
    payload.put("requestedAt", Instant.now().toString());
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
        .exchangeToMono(response -> interpret(request, response))
        .timeout(timeout)
        .onErrorResume(error -> Mono.just(failed(request, error)));
  }

  @SuppressWarnings("unchecked")
  private Mono<ExecutionResult> interpret(
      ExecutionRequest request, org.springframework.web.reactive.function.client.ClientResponse response) {
    HttpStatusCode code = response.statusCode();
    if (code.is2xxSuccessful() || code.is4xxClientError()) {
      return response
          .bodyToMono(Map.class)
          .defaultIfEmpty(Map.of())
          .map(body -> completedOrDenied(request, body, code));
    }
    return response.releaseBody().thenReturn(ExecutionResult.unavailable());
  }

  private static ExecutionResult completedOrDenied(
      ExecutionRequest request, Map<?, ?> body, HttpStatusCode code) {
    Map<String, Object> result = ActionHubBibliotecaIdentity.validatedResult(request, body);
    if (result.isEmpty()) {
      return ExecutionResult.unavailable();
    }
    result.put("httpStatus", code.value());
    if (code.is4xxClientError() || "FAILED".equals(String.valueOf(body.get("status")))) {
      result.putIfAbsent("ok", Boolean.FALSE);
      result.put("businessOutcome", "DENIED");
    }
    return new ExecutionResult(
        true,
        "COMPLETED",
        request.requestId(),
        PROVIDER_ID,
        text(result.get("order_id")),
        "ACTIONHUB_BIBLIOTECA",
        SatelliteContractV1.WATERMARK_BIBLIOTECA,
        List.of(),
        List.of(),
        result);
  }

  private static ExecutionResult failed(ExecutionRequest request, Throwable error) {
    Throwable unwrapped = Exceptions.unwrap(error);
    if (unwrapped instanceof TimeoutException
        || error instanceof TimeoutException
        || BibliotecaStateProjection.mutating(request.capabilityId())
            && unwrapped instanceof WebClientResponseException web
            && web.getStatusCode().is5xxServerError()) {
      return new ExecutionResult(
          false,
          "UNKNOWN",
          request.requestId(),
          PROVIDER_ID,
          null,
          "ACTIONHUB_BIBLIOTECA",
          SatelliteContractV1.WATERMARK_BIBLIOTECA,
          List.of(),
          List.of(),
          Map.of("effectCertainty", "UNKNOWN"));
    }
    return ExecutionResult.unavailable();
  }

  private static String text(Object value) {
    return value == null ? null : String.valueOf(value);
  }
}
