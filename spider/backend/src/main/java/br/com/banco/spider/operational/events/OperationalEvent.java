package br.com.banco.spider.operational.events;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;

public record OperationalEvent(
    String eventId,
    int schemaVersion,
    OperationalEventType eventType,
    OperationalEventCategory category,
    Instant occurredAt,
    String executionId,
    String interactionId,
    String correlationId,
    String source,
    OperationalEventOutcome outcome,
    Long durationMs,
    Map<String, String> metadata) {

  public OperationalEvent {
    Objects.requireNonNull(eventId, "eventId");
    Objects.requireNonNull(eventType, "eventType");
    Objects.requireNonNull(category, "category");
    Objects.requireNonNull(occurredAt, "occurredAt");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(source, "source");
    if (schemaVersion != 1) {
      throw new IllegalArgumentException("Only schemaVersion 1 is supported");
    }
    metadata = metadata == null ? Map.of() : Map.copyOf(metadata);
  }
}
