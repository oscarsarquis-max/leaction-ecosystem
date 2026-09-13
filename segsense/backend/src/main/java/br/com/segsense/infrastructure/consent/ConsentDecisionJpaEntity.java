package br.com.segsense.infrastructure.consent;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "consent_decision", schema = "segsense")
public class ConsentDecisionJpaEntity {

  @Id private UUID id;

  @Column(name = "instance_id", nullable = false)
  private UUID instanceId;

  @Column(name = "decision_type", nullable = false, length = 24)
  private String decisionType;

  @Column(name = "notice_version", nullable = false)
  private Integer noticeVersion;

  @Column(name = "notice_content_hash", nullable = false, length = 64)
  private String noticeContentHash;

  @Column(name = "covered_fields_hash", nullable = false, length = 64)
  private String coveredFieldsHash;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  @Column(name = "correlation_id", nullable = false)
  private UUID correlationId;

  @Column(name = "instance_version_before", nullable = false)
  private Long instanceVersionBefore;

  @Column(name = "instance_version_after", nullable = false)
  private Long instanceVersionAfter;

  @Column(nullable = false, length = 32)
  private String actor;

  protected ConsentDecisionJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public UUID getInstanceId() {
    return instanceId;
  }

  public void setInstanceId(UUID instanceId) {
    this.instanceId = instanceId;
  }

  public String getDecisionType() {
    return decisionType;
  }

  public void setDecisionType(String decisionType) {
    this.decisionType = decisionType;
  }

  public Integer getNoticeVersion() {
    return noticeVersion;
  }

  public void setNoticeVersion(Integer noticeVersion) {
    this.noticeVersion = noticeVersion;
  }

  public String getNoticeContentHash() {
    return noticeContentHash;
  }

  public void setNoticeContentHash(String noticeContentHash) {
    this.noticeContentHash = noticeContentHash;
  }

  public String getCoveredFieldsHash() {
    return coveredFieldsHash;
  }

  public void setCoveredFieldsHash(String coveredFieldsHash) {
    this.coveredFieldsHash = coveredFieldsHash;
  }

  public Instant getOccurredAt() {
    return occurredAt;
  }

  public void setOccurredAt(Instant occurredAt) {
    this.occurredAt = occurredAt;
  }

  public UUID getCorrelationId() {
    return correlationId;
  }

  public void setCorrelationId(UUID correlationId) {
    this.correlationId = correlationId;
  }

  public Long getInstanceVersionBefore() {
    return instanceVersionBefore;
  }

  public void setInstanceVersionBefore(Long instanceVersionBefore) {
    this.instanceVersionBefore = instanceVersionBefore;
  }

  public Long getInstanceVersionAfter() {
    return instanceVersionAfter;
  }

  public void setInstanceVersionAfter(Long instanceVersionAfter) {
    this.instanceVersionAfter = instanceVersionAfter;
  }

  public String getActor() {
    return actor;
  }

  public void setActor(String actor) {
    this.actor = actor;
  }
}
