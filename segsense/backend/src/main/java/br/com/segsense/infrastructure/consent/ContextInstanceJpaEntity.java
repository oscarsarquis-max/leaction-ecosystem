package br.com.segsense.infrastructure.consent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "context_instance", schema = "segsense")
public class ContextInstanceJpaEntity {

  @Id private UUID id;

  @Column(name = "link_id", nullable = false)
  private UUID linkId;

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

  @Column(name = "notice_id", nullable = false)
  private UUID noticeId;

  @Column(name = "notice_version", nullable = false)
  private Integer noticeVersion;

  @Column(name = "notice_snapshot_id", nullable = false)
  private UUID noticeSnapshotId;

  @Column(name = "notice_content_hash", nullable = false, length = 64)
  private String noticeContentHash;

  @Column(name = "credential_digest", nullable = false, columnDefinition = "BYTEA")
  private byte[] credentialDigest;

  @Column(name = "credential_hint", nullable = false, length = 8)
  private String credentialHint;

  @Column(name = "idempotency_key_digest", columnDefinition = "BYTEA")
  private byte[] idempotencyKeyDigest;

  @Column(nullable = false, length = 32)
  private String status;

  @Column(name = "values_unavailable", nullable = false)
  private boolean valuesUnavailable;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Version
  @Column(nullable = false)
  private Long version;

  @Column(name = "created_correlation_id", nullable = false)
  private UUID createdCorrelationId;

  protected ContextInstanceJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getLinkId() {
    return linkId;
  }

  public void setLinkId(UUID linkId) {
    this.linkId = linkId;
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

  public UUID getNoticeId() {
    return noticeId;
  }

  public void setNoticeId(UUID noticeId) {
    this.noticeId = noticeId;
  }

  public Integer getNoticeVersion() {
    return noticeVersion;
  }

  public void setNoticeVersion(Integer noticeVersion) {
    this.noticeVersion = noticeVersion;
  }

  public UUID getNoticeSnapshotId() {
    return noticeSnapshotId;
  }

  public void setNoticeSnapshotId(UUID noticeSnapshotId) {
    this.noticeSnapshotId = noticeSnapshotId;
  }

  public String getNoticeContentHash() {
    return noticeContentHash;
  }

  public void setNoticeContentHash(String noticeContentHash) {
    this.noticeContentHash = noticeContentHash;
  }

  public byte[] getCredentialDigest() {
    return credentialDigest;
  }

  public void setCredentialDigest(byte[] credentialDigest) {
    this.credentialDigest = credentialDigest;
  }

  public String getCredentialHint() {
    return credentialHint;
  }

  public void setCredentialHint(String credentialHint) {
    this.credentialHint = credentialHint;
  }

  public byte[] getIdempotencyKeyDigest() {
    return idempotencyKeyDigest;
  }

  public void setIdempotencyKeyDigest(byte[] idempotencyKeyDigest) {
    this.idempotencyKeyDigest = idempotencyKeyDigest;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public boolean isValuesUnavailable() {
    return valuesUnavailable;
  }

  public void setValuesUnavailable(boolean valuesUnavailable) {
    this.valuesUnavailable = valuesUnavailable;
  }

  public Instant getExpiresAt() {
    return expiresAt;
  }

  public void setExpiresAt(Instant expiresAt) {
    this.expiresAt = expiresAt;
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

  public Long getVersion() {
    return version;
  }

  public void setVersion(Long version) {
    this.version = version;
  }

  public UUID getCreatedCorrelationId() {
    return createdCorrelationId;
  }

  public void setCreatedCorrelationId(UUID createdCorrelationId) {
    this.createdCorrelationId = createdCorrelationId;
  }
}
