package br.com.banco.spider.operational.readmodel;

import java.time.Instant;
import java.util.List;

public record OperationalTimelineEvent(
    String eventId,
    Instant occurredAt,
    long sequence,
    OperationalTimelinePhase phase,
    String eventType,
    String state,
    String severity,
    String title,
    String safeDescription,
    String stepRef,
    Integer attemptNumber,
    Long durationMs,
    String traceRef,
    List<String> evidenceRefs,
    String source) {}
