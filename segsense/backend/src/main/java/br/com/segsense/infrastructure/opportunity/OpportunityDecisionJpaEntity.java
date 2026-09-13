package br.com.segsense.infrastructure.opportunity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;
import org.hibernate.annotations.Immutable;

@Entity
@Immutable
@Table(name = "opportunity_decision", schema = "segsense")
public class OpportunityDecisionJpaEntity {

  @Id private UUID id;

  @Column(name = "submission_id", nullable = false)
  private UUID submissionId;

  @Column(name = "opportunity_id", nullable = false)
  private UUID opportunityId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(nullable = false, length = 16)
  private String outcome;

  @Column(name = "decided_at", nullable = false)
  private Instant decidedAt;

  @Column(name = "decided_by", nullable = false, length = 128)
  private String decidedBy;

  @Column(length = 500)
  private String justification;

  @Column(name = "correlation_id", nullable = false)
  private UUID correlationId;

  protected OpportunityDecisionJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getSubmissionId() {
    return submissionId;
  }

  public void setSubmissionId(UUID submissionId) {
    this.submissionId = submissionId;
  }

  public UUID getOpportunityId() {
    return opportunityId;
  }

  public void setOpportunityId(UUID opportunityId) {
    this.opportunityId = opportunityId;
  }

  public Integer getRevisionNumber() {
    return revisionNumber;
  }

  public void setRevisionNumber(Integer revisionNumber) {
    this.revisionNumber = revisionNumber;
  }

  public String getOutcome() {
    return outcome;
  }

  public void setOutcome(String outcome) {
    this.outcome = outcome;
  }

  public Instant getDecidedAt() {
    return decidedAt;
  }

  public void setDecidedAt(Instant decidedAt) {
    this.decidedAt = decidedAt;
  }

  public String getDecidedBy() {
    return decidedBy;
  }

  public void setDecidedBy(String decidedBy) {
    this.decidedBy = decidedBy;
  }

  public String getJustification() {
    return justification;
  }

  public void setJustification(String justification) {
    this.justification = justification;
  }

  public UUID getCorrelationId() {
    return correlationId;
  }

  public void setCorrelationId(UUID correlationId) {
    this.correlationId = correlationId;
  }
}
