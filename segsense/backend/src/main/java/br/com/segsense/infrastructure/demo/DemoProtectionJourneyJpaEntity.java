package br.com.segsense.infrastructure.demo;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "demo_protection_journey", schema = "segsense")
public class DemoProtectionJourneyJpaEntity {

  @Id
  private UUID id;

  @Column(name = "scenario_key", nullable = false, length = 80)
  private String scenarioKey;

  @Column(name = "declared_objective", nullable = false, length = 80)
  private String declaredObjective;

  @Column(nullable = false, length = 32)
  private String status;

  @Column(name = "correlation_id", nullable = false, length = 36)
  private String correlationId;

  @Column(name = "idempotency_key_hash", nullable = false, length = 64)
  private String idempotencyKeyHash;

  @Column(name = "spider_decision_id", length = 80)
  private String spiderDecisionId;

  @Column(name = "mock_result_id", length = 80)
  private String mockResultId;

  @Column(name = "failure_kind", length = 16)
  private String failureKind;

  @Column(name = "projection_json", nullable = false, columnDefinition = "TEXT")
  private String projectionJson;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Column(name = "request_fingerprint", length = 64)
  private String requestFingerprint;

  protected DemoProtectionJourneyJpaEntity() {}

  public UUID getId() {
    return id;
  }

  public void setId(UUID id) {
    this.id = id;
  }

  public String getScenarioKey() {
    return scenarioKey;
  }

  public void setScenarioKey(String scenarioKey) {
    this.scenarioKey = scenarioKey;
  }

  public String getDeclaredObjective() {
    return declaredObjective;
  }

  public void setDeclaredObjective(String declaredObjective) {
    this.declaredObjective = declaredObjective;
  }

  public String getStatus() {
    return status;
  }

  public void setStatus(String status) {
    this.status = status;
  }

  public String getCorrelationId() {
    return correlationId;
  }

  public void setCorrelationId(String correlationId) {
    this.correlationId = correlationId;
  }

  public String getIdempotencyKeyHash() {
    return idempotencyKeyHash;
  }

  public void setIdempotencyKeyHash(String idempotencyKeyHash) {
    this.idempotencyKeyHash = idempotencyKeyHash;
  }

  public String getSpiderDecisionId() {
    return spiderDecisionId;
  }

  public void setSpiderDecisionId(String spiderDecisionId) {
    this.spiderDecisionId = spiderDecisionId;
  }

  public String getMockResultId() {
    return mockResultId;
  }

  public void setMockResultId(String mockResultId) {
    this.mockResultId = mockResultId;
  }

  public String getFailureKind() {
    return failureKind;
  }

  public void setFailureKind(String failureKind) {
    this.failureKind = failureKind;
  }

  public String getProjectionJson() {
    return projectionJson;
  }

  public void setProjectionJson(String projectionJson) {
    this.projectionJson = projectionJson;
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

  public String getRequestFingerprint() {
    return requestFingerprint;
  }

  public void setRequestFingerprint(String requestFingerprint) {
    this.requestFingerprint = requestFingerprint;
  }
}
