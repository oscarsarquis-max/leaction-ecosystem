package br.com.segsense.infrastructure.consent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "consent_notice_decision", schema = "segsense")
public class ConsentNoticeDecisionJpaEntity {

  @Id private UUID id;

  @Column(name = "notice_id", nullable = false)
  private UUID noticeId;

  @Column(name = "notice_version", nullable = false)
  private Integer noticeVersion;

  @Column(name = "content_hash", nullable = false, length = 64)
  private String contentHash;

  @Column(name = "decision_type", nullable = false, length = 16)
  private String decisionType;

  @Column(nullable = false, length = 500)
  private String justification;

  @Column(nullable = false, length = 128)
  private String actor;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  protected ConsentNoticeDecisionJpaEntity() {}

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

  public Integer getNoticeVersion() {
    return noticeVersion;
  }

  public void setNoticeVersion(Integer noticeVersion) {
    this.noticeVersion = noticeVersion;
  }

  public String getContentHash() {
    return contentHash;
  }

  public void setContentHash(String contentHash) {
    this.contentHash = contentHash;
  }

  public String getDecisionType() {
    return decisionType;
  }

  public void setDecisionType(String decisionType) {
    this.decisionType = decisionType;
  }

  public String getJustification() {
    return justification;
  }

  public void setJustification(String justification) {
    this.justification = justification;
  }

  public String getActor() {
    return actor;
  }

  public void setActor(String actor) {
    this.actor = actor;
  }

  public Instant getOccurredAt() {
    return occurredAt;
  }

  public void setOccurredAt(Instant occurredAt) {
    this.occurredAt = occurredAt;
  }
}
