package br.com.segsense.domain.opportunity;

import java.time.Instant;
import java.util.Objects;
import java.util.UUID;

public record OpportunitySubmission(
    UUID id,
    UUID opportunityId,
    int revisionNumber,
    Instant submittedAt,
    String submittedBy,
    UUID correlationId,
    SubmissionStatus status) {

  public OpportunitySubmission {
    Objects.requireNonNull(id, "id");
    Objects.requireNonNull(opportunityId, "opportunityId");
    Objects.requireNonNull(submittedAt, "submittedAt");
    Objects.requireNonNull(submittedBy, "submittedBy");
    Objects.requireNonNull(correlationId, "correlationId");
    Objects.requireNonNull(status, "status");
  }
}
