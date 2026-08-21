package br.com.banco.spider.execution.callback.delivery;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusDisposition;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQuery;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQueryPort;
import br.com.banco.spider.execution.callback.CallbackDeliveryStatusQueryResult;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import reactor.core.publisher.Mono;

/** Mock Status Query Adapter — cenários determinísticos, sem rede/sleep. */
public class MockCallbackDeliveryStatusQueryAdapter implements CallbackDeliveryStatusQueryPort {

  public enum Scenario {
    CONFIRMED_DELIVERED,
    ACCEPTED_THEN_DELIVERED,
    NOT_FOUND_THEN_DELIVERED,
    CONFIRMED_NOT_FOUND,
    CONFIRMED_REJECTED,
    RETRYABLE_FAILURE_THEN_DELIVERED,
    PERMANENT_QUERY_FAILURE,
    TIMEOUT,
    UNKNOWN
  }

  private final Scenario scenario;
  private final SpiderClock clock;
  private final Duration visibilityGrace;
  private final Map<String, AtomicInteger> queriesByKey = new ConcurrentHashMap<>();
  private final AtomicInteger totalQueries = new AtomicInteger();

  public MockCallbackDeliveryStatusQueryAdapter(Scenario scenario, SpiderClock clock) {
    this(scenario, clock, Duration.ofMillis(100));
  }

  public MockCallbackDeliveryStatusQueryAdapter(
      Scenario scenario, SpiderClock clock, Duration visibilityGrace) {
    this.scenario = scenario;
    this.clock = clock;
    this.visibilityGrace = visibilityGrace;
  }

  public int totalQueries() {
    return totalQueries.get();
  }

  public int queriesFor(String deliveryKey) {
    return queriesByKey.getOrDefault(deliveryKey, new AtomicInteger()).get();
  }

  @Override
  public Mono<CallbackDeliveryStatusQueryResult> query(CallbackDeliveryStatusQuery query) {
    totalQueries.incrementAndGet();
    int n =
        queriesByKey
            .computeIfAbsent(query.deliveryKey(), k -> new AtomicInteger())
            .incrementAndGet();
    Instant now = clock.now();
    return Mono.just(resolve(n, now));
  }

  private CallbackDeliveryStatusQueryResult resolve(int attempt, Instant now) {
    return switch (scenario) {
      case CONFIRMED_DELIVERED ->
          CallbackDeliveryStatusQueryResult.of(
              CallbackDeliveryStatusDisposition.CONFIRMED_DELIVERED, now);
      case ACCEPTED_THEN_DELIVERED ->
          attempt == 1
              ? CallbackDeliveryStatusQueryResult.of(
                  CallbackDeliveryStatusDisposition.ACCEPTED_NOT_FINAL, now)
              : CallbackDeliveryStatusQueryResult.of(
                  CallbackDeliveryStatusDisposition.CONFIRMED_DELIVERED, now);
      case NOT_FOUND_THEN_DELIVERED ->
          attempt == 1
              ? CallbackDeliveryStatusQueryResult.of(
                  CallbackDeliveryStatusDisposition.CONFIRMED_NOT_FOUND, now)
              : CallbackDeliveryStatusQueryResult.of(
                  CallbackDeliveryStatusDisposition.CONFIRMED_DELIVERED, now);
      case CONFIRMED_NOT_FOUND ->
          CallbackDeliveryStatusQueryResult.of(
              CallbackDeliveryStatusDisposition.CONFIRMED_NOT_FOUND, now);
      case CONFIRMED_REJECTED ->
          CallbackDeliveryStatusQueryResult.of(
              CallbackDeliveryStatusDisposition.CONFIRMED_REJECTED, now);
      case RETRYABLE_FAILURE_THEN_DELIVERED ->
          attempt == 1
              ? new CallbackDeliveryStatusQueryResult(
                  CallbackDeliveryStatusDisposition.RETRYABLE_QUERY_FAILURE,
                  now,
                  null,
                  "503",
                  Duration.ofMillis(50),
                  error("QUERY_UNAVAILABLE", ErrorCategory.UNAVAILABLE),
                  null)
              : CallbackDeliveryStatusQueryResult.of(
                  CallbackDeliveryStatusDisposition.CONFIRMED_DELIVERED, now);
      case PERMANENT_QUERY_FAILURE ->
          new CallbackDeliveryStatusQueryResult(
              CallbackDeliveryStatusDisposition.PERMANENT_QUERY_FAILURE,
              now,
              null,
              "400",
              null,
              error("QUERY_REJECTED", ErrorCategory.CONTRACT),
              null);
      case TIMEOUT ->
          new CallbackDeliveryStatusQueryResult(
              CallbackDeliveryStatusDisposition.RETRYABLE_QUERY_FAILURE,
              now,
              null,
              "TIMEOUT",
              null,
              error("QUERY_TIMEOUT", ErrorCategory.TIMEOUT),
              null);
      case UNKNOWN ->
          CallbackDeliveryStatusQueryResult.of(CallbackDeliveryStatusDisposition.UNKNOWN, now);
    };
  }

  public Duration visibilityGrace() {
    return visibilityGrace;
  }

  private static CanonicalError error(String code, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(code)
        .retryable(category == ErrorCategory.UNAVAILABLE || category == ErrorCategory.TIMEOUT)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("mock_status_query", null, null, null))
        .build();
  }
}
