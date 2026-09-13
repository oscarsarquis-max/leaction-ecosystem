package br.com.segsense.infrastructure.consent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "consent_notice_snapshot", schema = "segsense")
public class ConsentNoticeSnapshotJpaEntity {

  @Id private UUID id;

  @Column(name = "notice_id", nullable = false)
  private UUID noticeId;

  @Column(name = "version_number", nullable = false)
  private Integer versionNumber;

  @Column(name = "purpose_title", nullable = false, length = 140)
  private String purposeTitle;

  @Column(name = "purpose_description", nullable = false, length = 2000)
  private String purposeDescription;

  @Column(name = "transparency_text", nullable = false, length = 4000)
  private String transparencyText;

  @Column(name = "no_external_sharing_text", nullable = false, length = 500)
  private String noExternalSharingText;

  @Column(name = "content_hash", nullable = false, length = 64)
  private String contentHash;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "created_by", nullable = false, length = 128)
  private String createdBy;

  @Column(name = "opportunity_revision_id", nullable = false)
  private UUID opportunityRevisionId;

  protected ConsentNoticeSnapshotJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getNoticeId() {
    return noticeId;
  }

  public void setNoticeId(UUID noticeId) {
    this.noticeId = noticeId;
  }

  public Integer getVersionNumber() {
    return versionNumber;
  }

  public void setVersionNumber(Integer versionNumber) {
    this.versionNumber = versionNumber;
  }

  public String getPurposeTitle() {
    return purposeTitle;
  }

  public void setPurposeTitle(String purposeTitle) {
    this.purposeTitle = purposeTitle;
  }

  public String getPurposeDescription() {
    return purposeDescription;
  }

  public void setPurposeDescription(String purposeDescription) {
    this.purposeDescription = purposeDescription;
  }

  public String getTransparencyText() {
    return transparencyText;
  }

  public void setTransparencyText(String transparencyText) {
    this.transparencyText = transparencyText;
  }

  public String getNoExternalSharingText() {
    return noExternalSharingText;
  }

  public void setNoExternalSharingText(String noExternalSharingText) {
    this.noExternalSharingText = noExternalSharingText;
  }

  public String getContentHash() {
    return contentHash;
  }

  public void setContentHash(String contentHash) {
    this.contentHash = contentHash;
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

  public UUID getOpportunityRevisionId() {
    return opportunityRevisionId;
  }

  public void setOpportunityRevisionId(UUID opportunityRevisionId) {
    this.opportunityRevisionId = opportunityRevisionId;
  }
}
