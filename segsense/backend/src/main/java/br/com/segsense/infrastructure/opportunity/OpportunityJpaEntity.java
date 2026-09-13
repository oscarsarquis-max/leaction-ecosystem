package br.com.segsense.infrastructure.opportunity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "contextual_opportunity", schema = "segsense")
public class OpportunityJpaEntity {

  @Id
  private UUID id;

  @Column(name = "publisher_id", nullable = false)
  private UUID publisherId;

  @Column(name = "channel_id", nullable = false)
  private UUID channelId;

  @Column(name = "environment_id", nullable = false)
  private UUID environmentId;

  @Column(nullable = false, length = 50)
  private String key;

  @Column(nullable = false, length = 16)
  private String status;

  @Column(name = "current_revision", nullable = false)
  private Integer currentRevision;

  @Version
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

  @Column(name = "submitted_revision")
  private Integer submittedRevision;

  @Column(name = "approved_revision")
  private Integer approvedRevision;

  @Column(name = "open_submission_id")
  private UUID openSubmissionId;

  @Column(name = "submitted_by", length = 128)
  private String submittedBy;

  @Column(name = "approved_by", length = 128)
  private String approvedBy;

  protected OpportunityJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getPublisherId() {
    return publisherId;
  }

  public void setPublisherId(UUID publisherId) {
    this.publisherId = publisherId;
  }

  public UUID getChannelId() {
    return channelId;
  }

  public void setChannelId(UUID channelId) {
    this.channelId = channelId;
  }

  public UUID getEnvironmentId() {
    return environmentId;
  }

  public void setEnvironmentId(UUID environmentId) {
    this.environmentId = environmentId;
  }

  public String getKey() {
    return key;
  }

  public void setKey(String key) {
    this.key = key;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public Integer getCurrentRevision() {
    return currentRevision;
  }

  public void setCurrentRevision(Integer currentRevision) {
    this.currentRevision = currentRevision;
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

  public Integer getSubmittedRevision() {
    return submittedRevision;
  }

  public void setSubmittedRevision(Integer submittedRevision) {
    this.submittedRevision = submittedRevision;
  }

  public Integer getApprovedRevision() {
    return approvedRevision;
  }

  public void setApprovedRevision(Integer approvedRevision) {
    this.approvedRevision = approvedRevision;
  }

  public UUID getOpenSubmissionId() {
    return openSubmissionId;
  }

  public void setOpenSubmissionId(UUID openSubmissionId) {
    this.openSubmissionId = openSubmissionId;
  }

  public String getSubmittedBy() {
    return submittedBy;
  }

  public void setSubmittedBy(String submittedBy) {
    this.submittedBy = submittedBy;
  }

  public String getApprovedBy() {
    return approvedBy;
  }

  public void setApprovedBy(String approvedBy) {
    this.approvedBy = approvedBy;
  }
}
