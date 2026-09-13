package br.com.segsense.infrastructure.consent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "consent_notice", schema = "segsense")
public class ConsentNoticeJpaEntity {

  @Id private UUID id;

  @Column(name = "publisher_id", nullable = false)
  private UUID publisherId;

  @Column(name = "channel_id", nullable = false)
  private UUID channelId;

  @Column(name = "environment_id", nullable = false)
  private UUID environmentId;

  @Column(name = "opportunity_id", nullable = false)
  private UUID opportunityId;

  @Column(name = "revision_number", nullable = false)
  private Integer revisionNumber;

  @Column(name = "opportunity_revision_id", nullable = false)
  private UUID opportunityRevisionId;

  @Column(name = "current_version", nullable = false)
  private Integer currentVersion;

  @Column(name = "approved_version")
  private Integer approvedVersion;

  @Column(nullable = false, length = 16)
  private String status;

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

  protected ConsentNoticeJpaEntity() {}

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

  public UUID getOpportunityRevisionId() {
    return opportunityRevisionId;
  }

  public void setOpportunityRevisionId(UUID opportunityRevisionId) {
    this.opportunityRevisionId = opportunityRevisionId;
  }

  public Integer getCurrentVersion() {
    return currentVersion;
  }

  public void setCurrentVersion(Integer currentVersion) {
    this.currentVersion = currentVersion;
  }

  public Integer getApprovedVersion() {
    return approvedVersion;
  }

  public void setApprovedVersion(Integer approvedVersion) {
    this.approvedVersion = approvedVersion;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public Long getVersion() {
    return version;
  }

  public void setVersion(Long version) {
    this.version = version;
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
