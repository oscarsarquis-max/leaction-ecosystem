package br.com.segsense.domain.link;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record ContextLinkEvent(
    UUID id,
    UUID linkId,
    ContextLinkEventType eventType,
    Instant occurredAt,
    String actorSubject,
    UUID correlationId) {

  public ContextLinkEvent {
    Objects.requireNonNull(id, "id");
    Objects.requireNonNull(linkId, "linkId");
    Objects.requireNonNull(eventType, "eventType");
    Objects.requireNonNull(occurredAt, "occurredAt");
    Objects.requireNonNull(actorSubject, "actorSubject");
    Objects.requireNonNull(correlationId, "correlationId");
  }
}
