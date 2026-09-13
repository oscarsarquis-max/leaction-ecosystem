package br.com.segsense.inbound.http.link;

import java.time.Instant;
import java.util.UUID;

public record ContextLinkEventResponse(
    UUID id, String eventType, Instant occurredAt, String actorSubject, UUID correlationId) {}
