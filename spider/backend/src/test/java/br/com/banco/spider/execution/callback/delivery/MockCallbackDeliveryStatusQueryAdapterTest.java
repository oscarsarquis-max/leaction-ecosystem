package br.com.banco.spider.execution.callback.delivery;

import static org.junit.jupiter.api.Assertions.assertEquals;

import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQuery;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class MockCallbackDeliveryStatusQueryAdapterTest {

  private static final Instant NOW = Instant.parse("2026-08-21T16:00:00Z");

  private CallbackDeliveryStatusQuery query(int n) {
    return new CallbackDeliveryStatusQuery(
        "e1",
        "cb@1",
        "delivery-key-1",
        null,
        "contract",
        "binding",
        "sec",
        n,
        NOW.plusSeconds(5),
        "corr",
        null);
  }

  @Test
  void allScenariosAreDeterministic() {
    SpiderClock clock = SpiderClock.fixed(NOW);
    for (MockCallbackDeliveryStatusQueryAdapter.Scenario scenario :
        MockCallbackDeliveryStatusQueryAdapter.Scenario.values()) {
      MockCallbackDeliveryStatusQueryAdapter adapter =
          new MockCallbackDeliveryStatusQueryAdapter(scenario, clock);
      StepVerifier.create(adapter.query(query(1)))
          .assertNext(
              r -> {
                assertEquals(NOW, r.observedAt());
                assertEquals(
                    expectedFirst(scenario),
                    r.disposition(),
                    "scenario=" + scenario);
              })
          .verifyComplete();
    }
  }

  private static CallbackDeliveryStatusDisposition expectedFirst(
      MockCallbackDeliveryStatusQueryAdapter.Scenario scenario) {
    return switch (scenario) {
      case CONFIRMED_DELIVERED -> CallbackDeliveryStatusDisposition.CONFIRMED_DELIVERED;
      case ACCEPTED_THEN_DELIVERED -> CallbackDeliveryStatusDisposition.ACCEPTED_NOT_FINAL;
      case NOT_FOUND_THEN_DELIVERED, CONFIRMED_NOT_FOUND ->
          CallbackDeliveryStatusDisposition.CONFIRMED_NOT_FOUND;
      case CONFIRMED_REJECTED -> CallbackDeliveryStatusDisposition.CONFIRMED_REJECTED;
      case RETRYABLE_FAILURE_THEN_DELIVERED, TIMEOUT ->
          CallbackDeliveryStatusDisposition.RETRYABLE_QUERY_FAILURE;
      case PERMANENT_QUERY_FAILURE ->
          CallbackDeliveryStatusDisposition.PERMANENT_QUERY_FAILURE;
      case UNKNOWN -> CallbackDeliveryStatusDisposition.UNKNOWN;
    };
  }
}
