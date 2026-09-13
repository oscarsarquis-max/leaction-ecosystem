package br.com.banco.spider.demo.segsense;

import java.util.List;
import reactor.core.publisher.Mono;

public interface IllustrativeProtectionProviderPort {

  Mono<MockCall> illustrate(MockRequest request);

  record MockRequest(
      String correlationId, String decisionId, String scenarioKey, String declaredObjective) {}

  record MockItem(String code, String title, String kind, boolean notOfferable) {}

  record MockCall(
      boolean available,
      String resultId,
      String providerId,
      String origin,
      String watermark,
      List<MockItem> items,
      List<String> pendingForBroker) {

    public static MockCall unavailable() {
      return new MockCall(false, null, null, null, null, List.of(), List.of());
    }
  }
}
