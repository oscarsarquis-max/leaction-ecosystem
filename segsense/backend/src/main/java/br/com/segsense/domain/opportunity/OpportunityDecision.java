package br.com.segsense.domain.opportunity;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record OpportunityDecision(
    UUID id,
    UUID submissionId,
    UUID opportunityId,
    int revisionNumber,
    DecisionOutcome outcome,
    Instant decidedAt,
    String decidedBy,
    String justification,
    UUID correlationId) {

  public OpportunityDecision {
    Objects.requireNonNull(id, "id");
    Objects.requireNonNull(submissionId, "submissionId");
    Objects.requireNonNull(opportunityId, "opportunityId");
    Objects.requireNonNull(outcome, "outcome");
    Objects.requireNonNull(decidedAt, "decidedAt");
    Objects.requireNonNull(decidedBy, "decidedBy");
    Objects.requireNonNull(correlationId, "correlationId");
  }
}
