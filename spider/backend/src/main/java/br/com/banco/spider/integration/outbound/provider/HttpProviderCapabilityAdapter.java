package br.com.banco.spider.integration.outbound.provider;

import br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionRequest;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ExecutionResult;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort.ResultItem;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
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
    boolean homeQuote = SatelliteContractV1.HOME_QUOTE_CAPABILITY.equals(request.capabilityId());
    Duration timeout = provider.getTimeout() == null ? Duration.ofSeconds(3) : provider.getTimeout();
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", homeQuote ? "1.1" : "1.0");
    payload.put("requestId", request.requestId());
    payload.put("correlationId", request.correlationId());
    payload.put("decisionId", request.decisionId());
    payload.put("capabilityId", request.capabilityId());
    payload.put("capabilityVersion", "1.0");
    payload.put("purpose", request.purpose());
    payload.put("inputs", homeQuote ? quoteInputs(request) : Map.of("scenarioKey", request.scenarioKey() == null ? "" : request.scenarioKey()));
    payload.put("dataClassification", request.dataClassification());
    payload.put("requestedAt", homeQuote ? Instant.now().toString() : Instant.parse("2026-09-13T12:00:00Z").toString());
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
    if (!"ILLUSTRATIVE_NOT_ICATU_CONTRACT".equals(result.get("origin"))
        && !"NON_BINDING_DEMO".equals(result.get("origin"))) {
      return ExecutionResult.unavailable();
    }
    if ("NON_BINDING_DEMO".equals(result.get("origin"))) {
      Map<String, Object> quote = new LinkedHashMap<>();
      quote.put("kind", "SYNTHETIC_HOME_QUOTE");
      quote.put("origin", "NON_BINDING_DEMO");
      quote.put("currency", "BRL");
      quote.put("insuredAmountCents", result.get("insuredAmountCents"));
      quote.put("premiumAnnualCents", result.get("premiumAnnualCents"));
      quote.put("coverPeriodMonths", result.get("coverPeriodMonths"));
      quote.put("dwellingType", result.get("dwellingType"));
      quote.put("dwellingBps", result.get("dwellingBps"));
      quote.put("ratingRuleVersion", result.get("ratingRuleVersion"));
      quote.put("nearbyFiresDidNotAdjustPremium", result.get("nearbyFiresDidNotAdjustPremium"));
      quote.put("calculatedAt", result.get("calculatedAt"));
      quote.put("premises", result.get("premises"));
      quote.put("watermark", result.get("watermark"));
      quote.put("status", "NON_BINDING_DEMO");
      quote.put("humanCalculation", humanCalculation(result));
      return new ExecutionResult(
          true,
          "COMPLETED",
          request.requestId(),
          String.valueOf(body.get("providerId")),
          body.get("providerReference") == null ? null : String.valueOf(body.get("providerReference")),
          "NON_BINDING_DEMO",
          result.get("watermark") == null ? null : String.valueOf(result.get("watermark")),
          List.of(),
          List.of(),
          quote);
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
                  Boolean.TRUE.equals(item.get("notOfferable")),
                  item.get("needAddressed") == null ? null : String.valueOf(item.get("needAddressed")),
                  item.get("pertinence") == null ? null : String.valueOf(item.get("pertinence")),
                  item.get("limits") == null ? null : String.valueOf(item.get("limits"))));
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

  private static Map<String, Object> quoteInputs(ExecutionRequest request) {
    Map<String, String> raw = request.quoteInputs() == null ? Map.of() : request.quoteInputs();
    Map<String, Object> inputs = new LinkedHashMap<>();
    inputs.put("scenarioKey", request.scenarioKey() == null ? "" : request.scenarioKey());
    inputs.put("dwellingType", raw.getOrDefault("dwellingType", ""));
    inputs.put("insuredAmountCents", parseLong(raw.get("insuredAmountCents")));
    inputs.put("coverPeriodMonths", parseInt(raw.get("coverPeriodMonths")));
    inputs.put("ratingRuleVersion", raw.getOrDefault("ratingRuleVersion", "HOME_QUOTE_SYNTHETIC_V1"));
    return inputs;
  }

  private static long parseLong(String value) {
    try {
      return Long.parseLong(value);
    } catch (RuntimeException ignored) {
      return -1L;
    }
  }

  private static int parseInt(String value) {
    try {
      return Integer.parseInt(value);
    } catch (RuntimeException ignored) {
      return -1;
    }
  }

  private static String humanCalculation(Map<?, ?> result) {
    Object premium = result.get("premiumAnnualCents");
    Object capital = result.get("insuredAmountCents");
    Object bps = result.get("dwellingBps");
    Object dwelling = result.get("dwellingType");
    return "Prêmio anual simulado = capital declarado × "
        + String.valueOf(bps)
        + " bps, arredondado para centavos. Tipo "
        + dwelling
        + ". Capital "
        + capital
        + " centavos → prêmio "
        + premium
        + " centavos. Incêndios na fonte editorial não entram na conta.";
  }
}
