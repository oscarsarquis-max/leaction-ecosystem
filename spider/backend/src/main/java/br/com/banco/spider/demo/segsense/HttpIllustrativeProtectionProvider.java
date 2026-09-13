package br.com.banco.spider.demo.segsense;

import br.com.banco.spider.config.SegSenseDemoProperties;
import br.com.banco.spider.demo.segsense.IllustrativeProtectionProviderPort.MockCall;
import br.com.banco.spider.demo.segsense.IllustrativeProtectionProviderPort.MockItem;
import br.com.banco.spider.demo.segsense.IllustrativeProtectionProviderPort.MockRequest;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.reactive.function.client.WebClientResponseException;
import reactor.core.publisher.Mono;

public final class HttpIllustrativeProtectionProvider implements IllustrativeProtectionProviderPort {

  private final WebClient client;
  private final SegSenseDemoProperties properties;

  public HttpIllustrativeProtectionProvider(WebClient.Builder builder, SegSenseDemoProperties properties) {
    this.properties = properties;
    this.client = builder.baseUrl(properties.getMockBaseUrl()).build();
  }

  @Override
  public Mono<MockCall> illustrate(MockRequest request) {
    if (properties.getMockCredential() == null || properties.getMockCredential().isBlank()) {
      return Mono.just(MockCall.unavailable());
    }
    Duration timeout = properties.getTimeout() == null ? Duration.ofSeconds(3) : properties.getTimeout();
    return client
        .post()
        .uri("/v1/illustrative-protection-items")
        .contentType(MediaType.APPLICATION_JSON)
        .header("X-SEGSENSE-Mock-Credential", properties.getMockCredential())
        .header("X-Correlation-ID", request.correlationId())
        .bodyValue(
            Map.of(
                "contractVersion",
                "segsense-mock-contract-v1",
                "correlationId",
                request.correlationId(),
                "decisionId",
                request.decisionId(),
                "scenarioKey",
                request.scenarioKey(),
                "declaredObjective",
                request.declaredObjective()))
        .retrieve()
        .bodyToMono(Map.class)
        .timeout(timeout)
        .map(HttpIllustrativeProtectionProvider::ok)
        .onErrorResume(WebClientResponseException.class, ignored -> Mono.just(MockCall.unavailable()))
        .onErrorResume(ignored -> Mono.just(MockCall.unavailable()));
  }

  private static MockCall ok(Map<?, ?> body) {
    if (body == null || !"SEGSENSE_PROVIDER_MOCK".equals(body.get("providerId"))) {
      return MockCall.unavailable();
    }
    if (!"ILLUSTRATIVE_NOT_ICATU_CONTRACT".equals(body.get("origin"))) {
      return MockCall.unavailable();
    }
    List<MockItem> items = new ArrayList<>();
    if (body.get("items") instanceof List<?> rawItems) {
      for (Object raw : rawItems) {
        if (raw instanceof Map<?, ?> item) {
          items.add(
              new MockItem(
                  String.valueOf(item.get("code")),
                  String.valueOf(item.get("title")),
                  String.valueOf(item.get("kind")),
                  Boolean.TRUE.equals(item.get("notOfferable"))));
        }
      }
    }
    List<String> pending = new ArrayList<>();
    if (body.get("pendingForBroker") instanceof List<?> rawPending) {
      for (Object raw : rawPending) {
        pending.add(String.valueOf(raw));
      }
    }
    return new MockCall(
        true,
        String.valueOf(body.get("resultId")),
        String.valueOf(body.get("providerId")),
        String.valueOf(body.get("origin")),
        String.valueOf(body.get("watermark")),
        items,
        pending);
  }
}
