package br.com.segsense.infrastructure.demonstration;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "demonstration_story", schema = "segsense")
public class DemonstrationStoryJpaEntity {

  @Id
  private UUID id;

  @Column(name = "story_key", nullable = false, unique = true, length = 50)
  private String storyKey;

  @Column(name = "workflow_status", nullable = false, length = 16)
  private String workflowStatus;

  @Column(name = "publication_status", nullable = false, length = 16)
  private String publicationStatus;

  @Column(name = "current_revision", nullable = false)
  private Integer currentRevision;

  @Column(name = "published_revision")
  private Integer publishedRevision;

  @Column(name = "submitted_by", length = 128)
  private String submittedBy;

  @jakarta.persistence.Version
  @Column(nullable = false)
  private Long version;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Column(name = "created_by", nullable = false, length = 128)
  private String createdBy;

  @Column(name = "updated_by", nullable = false, length = 128)
  private String updatedBy;

  protected DemonstrationStoryJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public String getStoryKey() {
    return storyKey;
  }

  public void setStoryKey(String storyKey) {
    this.storyKey = storyKey;
  }

  public String getWorkflowStatus() {
    return workflowStatus;
  }

  public void setWorkflowStatus(String workflowStatus) {
    this.workflowStatus = workflowStatus;
  }

  public String getPublicationStatus() {
    return publicationStatus;
  }

  public void setPublicationStatus(String publicationStatus) {
    this.publicationStatus = publicationStatus;
  }

  public Integer getCurrentRevision() {
    return currentRevision;
  }

  public void setCurrentRevision(Integer currentRevision) {
    this.currentRevision = currentRevision;
  }

  public Integer getPublishedRevision() {
    return publishedRevision;
  }

  public void setPublishedRevision(Integer publishedRevision) {
    this.publishedRevision = publishedRevision;
  }

  public String getSubmittedBy() {
    return submittedBy;
  }

  public void setSubmittedBy(String submittedBy) {
    this.submittedBy = submittedBy;
  }

  public Long getVersion() {
    return version;
  }

  public Instant getCreatedAt() {
    return createdAt;
  }

  public void setCreatedAt(Instant createdAt) {
    this.createdAt = createdAt;
  }

  public Instant getUpdatedAt() {
    return updatedAt;
  }

  public void setUpdatedAt(Instant updatedAt) {
    this.updatedAt = updatedAt;
  }

  public String getCreatedBy() {
    return createdBy;
  }

  public void setCreatedBy(String createdBy) {
    this.createdBy = createdBy;
  }

  public String getUpdatedBy() {
    return updatedBy;
  }

  public void setUpdatedBy(String updatedBy) {
    this.updatedBy = updatedBy;
  }
}
