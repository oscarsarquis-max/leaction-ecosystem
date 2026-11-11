package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import java.time.Duration;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeoutException;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;
import reactor.util.retry.Retry;

public final class HttpActionHubPayCapabilityAdapter implements ProviderCapabilityPort {

  public static final String PROVIDER_ID = "actionhub-pay";
  public static final String SECRET_HEADER = "X-ActionHub-Pay-Credential";

  private final WebClient.Builder builder;
  private final SatelliteRegistry registry;

  public HttpActionHubPayCapabilityAdapter(WebClient.Builder builder, SatelliteRegistry registry) {
    this.builder = builder;
    this.registry = registry;
  }

  @Override
  public Mono<ExecutionResult> execute(ExecutionRequest request) {
    ProviderEntry provider = registry.resolveProvider(request.capabilityId());
    if (provider == null || provider.getSecret() == null || provider.getSecret().isBlank()) {
      return Mono.just(ExecutionResult.unavailable());
    }
    if (!SatelliteContractV1.isPayCapability(request.capabilityId())) {
      return Mono.just(ExecutionResult.unavailable());
    }
    if ("production".equalsIgnoreCase(provider.getEnvironment())
        && !SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS.equals(request.capabilityId())) {
      return Mono.just(ExecutionResult.unavailable());
    }
    Duration timeout = provider.getTimeout() == null ? Duration.ofSeconds(3) : provider.getTimeout();
    Map<String, Object> payload = outboundPayload(request);
    return builder
        .baseUrl(provider.getBaseUrl())
        .build()
        .post()
        .uri("/v1/provider/capabilities/{capabilityId}/executions", request.capabilityId())
        .contentType(MediaType.APPLICATION_JSON)
        .header(SECRET_HEADER, provider.getSecret())
        .header("X-Correlation-ID", request.correlationId() == null ? "" : request.correlationId())
        .header("X-Request-ID", request.requestId() == null ? "" : request.requestId())
        .bodyValue(payload)
        .retrieve()
        .bodyToMono(Map.class)
        .timeout(timeout)
        .retryWhen(
            Retry.backoff(2, Duration.ofMillis(200))
                .maxBackoff(Duration.ofSeconds(2))
                .filter(
                    error ->
                        error instanceof TimeoutException
                            || (error instanceof WebClientResponseException response
                                && response.getStatusCode().is5xxServerError())))
        .map(body -> ok(request, body))
        .onErrorResume(TimeoutException.class, ignored -> Mono.just(ExecutionResult.unknownEffect()))
        .onErrorResume(WebClientResponseException.class, ignored -> Mono.just(ExecutionResult.unavailable()))
        .onErrorResume(ignored -> Mono.just(ExecutionResult.unavailable()));
  }

  static Map<String, Object> outboundPayload(ExecutionRequest request) {
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", outboundContractVersion(request.capabilityId()));
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
    return payload;
  }

  static String outboundContractVersion(String capabilityId) {
    if (SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS.equals(capabilityId)) {
      return SatelliteContractV1.VERSION_1_4;
    }
    return SatelliteContractV1.VERSION_1_3;
  }

  static boolean returnedContractMatches(String sent, Map<?, ?> body) {
    if (body == null || body.get("contractVersion") == null) {
      return true;
    }
    return sent.equals(String.valueOf(body.get("contractVersion")));
  }

  private static ExecutionResult ok(ExecutionRequest request, Map<?, ?> body) {
    if (!returnedContractMatches(outboundContractVersion(request.capabilityId()), body)) {
      return ExecutionResult.unavailable();
    }
    Map<String, Object> quote =
        SatelliteContractV1.LIST_PAYMENT_TRANSACTIONS.equals(request.capabilityId())
            ? ActionHubPayListIdentity.validatedQuote(request, body)
            : ActionHubPayLookupIdentity.validatedQuote(request, body);
    if (quote.isEmpty()) {
      return ExecutionResult.unavailable();
    }
    return new ExecutionResult(
        true,
        "COMPLETED",
        request.requestId(),
        PROVIDER_ID,
        text(quote.get("providerReference")),
        text(quote.get("origin")),
        SatelliteContractV1.WATERMARK_FINANCIAL,
        List.of(),
        List.of(),
        quote);
  }

  private static String text(Object value) {
    return value == null ? null : String.valueOf(value);
  }
}
