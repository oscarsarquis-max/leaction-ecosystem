package br.com.segsense.inbound.http.opportunity;

import java.time.Instant;
import java.util.UUID;

public record LifecycleEventResponse(
    UUID id,
    UUID opportunityId,
    int revisionNumber,
    String eventType,
    String previousStatus,
    String newStatus,
    String actorSubjectId,
    Instant occurredAt,
    String justification,
    UUID correlationId) {}
