package br.com.segsense.infrastructure.demonstration;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "demonstration_decision", schema = "segsense")
public class DemonstrationDecisionJpaEntity {

  @Id
  private UUID id;

  @Column(name = "story_id", nullable = false)
  private UUID storyId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(nullable = false, length = 16)
  private String action;

  @Column(nullable = false, length = 128)
  private String actor;

  @Column(nullable = false)
  private String justification;

  @Column(name = "decided_at", nullable = false)
  private Instant decidedAt;

  protected DemonstrationDecisionJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getStoryId() {
    return storyId;
  }

  public void setStoryId(UUID storyId) {
    this.storyId = storyId;
  }

  public Integer getRevisionNumber() {
    return revisionNumber;
  }

  public void setRevisionNumber(Integer revisionNumber) {
    this.revisionNumber = revisionNumber;
  }

  public String getAction() {
    return action;
  }

  public void setAction(String action) {
    this.action = action;
  }

  public String getActor() {
    return actor;
  }

  public void setActor(String actor) {
    this.actor = actor;
  }

  public String getJustification() {
    return justification;
  }

  public void setJustification(String justification) {
    this.justification = justification;
  }

  public Instant getDecidedAt() {
    return decidedAt;
  }

  public void setDecidedAt(Instant decidedAt) {
    this.decidedAt = decidedAt;
  }
}
