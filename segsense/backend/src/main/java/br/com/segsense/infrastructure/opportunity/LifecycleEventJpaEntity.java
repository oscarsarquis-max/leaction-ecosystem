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
@Table(name = "opportunity_lifecycle_event", schema = "segsense")
public class LifecycleEventJpaEntity {

  @Id private UUID id;

  @Column(name = "opportunity_id", nullable = false)
  private UUID opportunityId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(name = "event_type", nullable = false, length = 32)
  private String eventType;

  @Column(name = "previous_status", nullable = false, length = 16)
  private String previousStatus;

  @Column(name = "new_status", nullable = false, length = 16)
  private String newStatus;

  @Column(name = "actor_subject_id", nullable = false, length = 128)
  private String actorSubjectId;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  @Column(length = 500)
  private String justification;

  @Column(name = "correlation_id", nullable = false)
  private UUID correlationId;

  protected LifecycleEventJpaEntity() {}

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

  public String getEventType() {
    return eventType;
  }

  public void setEventType(String eventType) {
    this.eventType = eventType;
  }

  public String getPreviousStatus() {
    return previousStatus;
  }

  public void setPreviousStatus(String previousStatus) {
    this.previousStatus = previousStatus;
  }

  public String getNewStatus() {
    return newStatus;
  }

  public void setNewStatus(String newStatus) {
    this.newStatus = newStatus;
  }

  public String getActorSubjectId() {
    return actorSubjectId;
  }

  public void setActorSubjectId(String actorSubjectId) {
    this.actorSubjectId = actorSubjectId;
  }

  public Instant getOccurredAt() {
    return occurredAt;
  }

  public void setOccurredAt(Instant occurredAt) {
    this.occurredAt = occurredAt;
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
