package br.com.segsense.infrastructure.link;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "published_context_link", schema = "segsense")
public class PublishedContextLinkJpaEntity {

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

  @Column(name = "placement_key", nullable = false, length = 80)
  private String placementKey;

  @Column(nullable = false, length = 120)
  private String label;

  @Column(name = "token_digest", nullable = false, columnDefinition = "BYTEA")
  private byte[] tokenDigest;

  @Column(name = "token_hint", nullable = false, length = 8)
  private String tokenHint;

  @Column(nullable = false, length = 16)
  private String status;

  @Column(name = "issued_at", nullable = false)
  private Instant issuedAt;

  @Column(name = "issued_by", nullable = false, length = 128)
  private String issuedBy;

  @Column(name = "expires_at", nullable = false)
  private Instant expiresAt;

  @Column(name = "revoked_at")
  private Instant revokedAt;

  @Column(name = "revoked_by", length = 128)
  private String revokedBy;

  @Column(name = "revocation_reason", length = 500)
  private String revocationReason;

  @Version
  @Column(nullable = false)
  private Long version;

  @Column(name = "issued_correlation_id", nullable = false)
  private UUID issuedCorrelationId;

  @Column(name = "revoked_correlation_id")
  private UUID revokedCorrelationId;

  protected PublishedContextLinkJpaEntity() {}

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

  public String getPlacementKey() {
    return placementKey;
  }

  public void setPlacementKey(String placementKey) {
    this.placementKey = placementKey;
  }

  public String getLabel() {
    return label;
  }

  public void setLabel(String label) {
    this.label = label;
  }

  public byte[] getTokenDigest() {
    return tokenDigest;
  }

  public void setTokenDigest(byte[] tokenDigest) {
    this.tokenDigest = tokenDigest;
  }

  public String getTokenHint() {
    return tokenHint;
  }

  public void setTokenHint(String tokenHint) {
    this.tokenHint = tokenHint;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public Instant getIssuedAt() {
    return issuedAt;
  }

  public void setIssuedAt(Instant issuedAt) {
    this.issuedAt = issuedAt;
  }

  public String getIssuedBy() {
    return issuedBy;
  }

  public void setIssuedBy(String issuedBy) {
    this.issuedBy = issuedBy;
  }

  public Instant getExpiresAt() {
    return expiresAt;
  }

  public void setExpiresAt(Instant expiresAt) {
    this.expiresAt = expiresAt;
  }

  public Instant getRevokedAt() {
    return revokedAt;
  }

  public void setRevokedAt(Instant revokedAt) {
    this.revokedAt = revokedAt;
  }

  public String getRevokedBy() {
    return revokedBy;
  }

  public void setRevokedBy(String revokedBy) {
    this.revokedBy = revokedBy;
  }

  public String getRevocationReason() {
    return revocationReason;
  }

  public void setRevocationReason(String revocationReason) {
    this.revocationReason = revocationReason;
  }

  public Long getVersion() {
    return version;
  }

  public void setVersion(Long version) {
    this.version = version;
  }

  public UUID getIssuedCorrelationId() {
    return issuedCorrelationId;
  }

  public void setIssuedCorrelationId(UUID issuedCorrelationId) {
    this.issuedCorrelationId = issuedCorrelationId;
  }

  public UUID getRevokedCorrelationId() {
    return revokedCorrelationId;
  }

  public void setRevokedCorrelationId(UUID revokedCorrelationId) {
    this.revokedCorrelationId = revokedCorrelationId;
  }
}
