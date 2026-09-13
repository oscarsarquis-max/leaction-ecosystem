package br.com.segsense.infrastructure.opportunity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "contextual_opportunity_revision", schema = "segsense")
public class OpportunityRevisionJpaEntity {

  @Id
  private UUID id;

  @Column(name = "opportunity_id", nullable = false)
  private UUID opportunityId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(nullable = false, length = 140)
  private String title;

  @Column(name = "context_mode", nullable = false, length = 16)
  private String contextMode;

  @Column(name = "context_summary_template", nullable = false, length = 1000)
  private String contextSummaryTemplate;

  @Column(name = "objective_template", nullable = false, length = 1000)
  private String objectiveTemplate;

  @Column(name = "call_to_action_label", nullable = false, length = 80)
  private String callToActionLabel;

  @Column(name = "valid_from")
  private Instant validFrom;

  @Column(name = "valid_until")
  private Instant validUntil;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "created_by", nullable = false, length = 128)
  private String createdBy;

  protected OpportunityRevisionJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
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

  public String getTitle() {
    return title;
  }

  public void setTitle(String title) {
    this.title = title;
  }

  public String getContextMode() {
    return contextMode;
  }

  public void setContextMode(String contextMode) {
    this.contextMode = contextMode;
  }

  public String getContextSummaryTemplate() {
    return contextSummaryTemplate;
  }

  public void setContextSummaryTemplate(String contextSummaryTemplate) {
    this.contextSummaryTemplate = contextSummaryTemplate;
  }

  public String getObjectiveTemplate() {
    return objectiveTemplate;
  }

  public void setObjectiveTemplate(String objectiveTemplate) {
    this.objectiveTemplate = objectiveTemplate;
  }

  public String getCallToActionLabel() {
    return callToActionLabel;
  }

  public void setCallToActionLabel(String callToActionLabel) {
    this.callToActionLabel = callToActionLabel;
  }

  public Instant getValidFrom() {
    return validFrom;
  }

  public void setValidFrom(Instant validFrom) {
    this.validFrom = validFrom;
  }

  public Instant getValidUntil() {
    return validUntil;
  }

  public void setValidUntil(Instant validUntil) {
    this.validUntil = validUntil;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public void setCreatedAt(Instant createdAt) {
    this.createdAt = createdAt;
  }

  public String getCreatedBy() {
    return createdBy;
  }

  public void setCreatedBy(String createdBy) {
    this.createdBy = createdBy;
  }
}
