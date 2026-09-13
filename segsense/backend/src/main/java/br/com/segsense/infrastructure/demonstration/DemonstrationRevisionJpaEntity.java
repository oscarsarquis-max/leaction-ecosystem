package br.com.segsense.infrastructure.demonstration;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "demonstration_revision", schema = "segsense")
public class DemonstrationRevisionJpaEntity {

  @Id
  private UUID id;

  @Column(name = "story_id", nullable = false)
  private UUID storyId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(nullable = false, length = 200)
  private String title;

  @Column(nullable = false)
  private String summary;

  @Column(name = "intended_audience", nullable = false, length = 200)
  private String intendedAudience;

  @Column(name = "scope_note", nullable = false)
  private String scopeNote;

  @Column(nullable = false)
  private boolean frozen;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "created_by", nullable = false, length = 128)
  private String createdBy;

  protected DemonstrationRevisionJpaEntity() {}

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

  public String getTitle() {
    return title;
  }

  public void setTitle(String title) {
    this.title = title;
  }

  public String getSummary() {
    return summary;
  }

  public void setSummary(String summary) {
    this.summary = summary;
  }

  public String getIntendedAudience() {
    return intendedAudience;
  }

  public void setIntendedAudience(String intendedAudience) {
    this.intendedAudience = intendedAudience;
  }

  public String getScopeNote() {
    return scopeNote;
  }

  public void setScopeNote(String scopeNote) {
    this.scopeNote = scopeNote;
  }

  public boolean isFrozen() {
    return frozen;
  }

  public void setFrozen(boolean frozen) {
    this.frozen = frozen;
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
