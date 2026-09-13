package br.com.segsense.domain.opportunity;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record LifecycleEvent(
    UUID id,
    UUID opportunityId,
    int revisionNumber,
    LifecycleEventType type,
    OpportunityStatus previousStatus,
    OpportunityStatus newStatus,
    String actorSubjectId,
    Instant occurredAt,
    String justification,
    UUID correlationId) {

  public LifecycleEvent {
    Objects.requireNonNull(id, "id");
    Objects.requireNonNull(opportunityId, "opportunityId");
    Objects.requireNonNull(type, "type");
    Objects.requireNonNull(previousStatus, "previousStatus");
    Objects.requireNonNull(newStatus, "newStatus");
    Objects.requireNonNull(actorSubjectId, "actorSubjectId");
    Objects.requireNonNull(occurredAt, "occurredAt");
    Objects.requireNonNull(correlationId, "correlationId");
  }
}
