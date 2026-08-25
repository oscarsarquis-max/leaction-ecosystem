package br.com.banco.spider.operational.events;

import java.time.Duration;
import java.time.Instant;

public final class OperationalEventEmit {

  private OperationalEventEmit() {}

  public static void publish(
      OperationalEventPublisher publisher, OperationalEventDraft draft) {
    try {
      publisher.publish(draft);
    } catch (Throwable ignored) {
      // Operational telemetry is always fail-open for business execution.
    }
  }

  public static OperationalEventDraft draft(
      OperationalEventType type,
      String executionId,
      String correlationId,
      String source,
      OperationalEventOutcome outcome,
      Long durationMs,
      OperationalEventAttributes attributes) {
    return OperationalEventDraft.builder()
        .eventType(type)
        .executionId(executionId)
        .correlationId(correlationId)
        .source(source)
        .outcome(outcome)
        .durationMs(durationMs)
        .attributes(attributes)
        .build();
  }

  public static Long durationMs(Instant startedAt, Instant endedAt) {
    if (startedAt == null || endedAt == null) {
      return null;
    }
    return Math.max(0, Duration.between(startedAt, endedAt).toMillis());
  }
}
