package br.com.banco.spider.operational.readmodel;

import br.com.banco.spider.operational.events.OperationalEventCategory;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Instant;
import java.util.Map;

public record OperationalEventView(
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
    Map<String, String> metadata) {}
