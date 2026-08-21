package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.Objects;

public record GovernanceAuditEvent(
    String eventId,
    String commandType,
    String targetType,
    String targetRef,
    String actorPrincipalRef,
    String outcome,
    String reasonCode,
    String previousLifecycleState,
    String newLifecycleState,
    Instant occurredAt,
    String correlationId) {

  public GovernanceAuditEvent {
    Objects.requireNonNull(eventId, "eventId");
    Objects.requireNonNull(commandType, "commandType");
    Objects.requireNonNull(actorPrincipalRef, "actorPrincipalRef");
    Objects.requireNonNull(outcome, "outcome");
    Objects.requireNonNull(occurredAt, "occurredAt");
  }
}
