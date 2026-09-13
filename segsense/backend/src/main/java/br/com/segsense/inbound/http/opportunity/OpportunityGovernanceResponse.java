package br.com.segsense.inbound.http.opportunity;

import java.time.Instant;
import java.util.List;
import java.util.UUID;

public record OpportunityGovernanceResponse(
    UUID opportunityId,
    String status,
    int currentRevision,
    Integer submittedRevision,
    Integer approvedRevision,
    UUID openSubmissionId,
    String submittedBy,
    String approvedBy,
    long version,
    boolean effectivelyAvailable,
    boolean effectivelyPublishable,
    boolean effectivelyPublished,
    boolean windowOpen,
    boolean windowExpired,
    String publishedMeans,
    DecisionSnapshot latestDecision,
    List<String> availableActions) {

  public record DecisionSnapshot(
      UUID id,
      UUID submissionId,
      int revisionNumber,
      String outcome,
      Instant decidedAt,
      String decidedBy,
      String justification) {}
}
