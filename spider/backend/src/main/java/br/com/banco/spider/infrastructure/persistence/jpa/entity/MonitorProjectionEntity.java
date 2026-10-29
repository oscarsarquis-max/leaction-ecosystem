package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_monitor_projection")
@Getter
@Setter
@NoArgsConstructor
public class MonitorProjectionEntity {

  @Id
  @Column(name = "record_id", length = 200)
  private String recordId;

  @Column(nullable = false, length = 40)
  private String kind;

  @Column(name = "satellite_id", length = 80)
  private String satelliteId;

  @Column(name = "satellite_role", length = 40)
  private String satelliteRole;

  @Column(length = 80)
  private String origin;

  @Column(name = "message_id", length = 120)
  private String messageId;

  @Column(name = "correlation_id", length = 200)
  private String correlationId;

  @Column(name = "execution_id", length = 120)
  private String executionId;

  @Column(name = "external_ref", length = 120)
  private String externalRef;

  @Column(length = 80)
  private String capability;

  @Column(name = "contract_version", length = 20)
  private String contractVersion;

  @Column(name = "company_id", length = 80)
  private String companyId;

  @Column(length = 40)
  private String environment;

  @Column(name = "technical_state", length = 80)
  private String technicalState;

  @Column(name = "commercial_state", length = 80)
  private String commercialState;

  @Column(name = "financial_state", length = 80)
  private String financialState;

  @Column(name = "credit_state", length = 80)
  private String creditState;

  @Column(name = "current_component", length = 80)
  private String currentComponent;

  @Column(length = 120)
  private String objective;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "updated_at", nullable = false)
  private Instant updatedAt;

  @Column(name = "last_synced_at")
  private Instant lastSyncedAt;

  @Column(name = "discovery_origin", length = 40)
  private String discoveryOrigin;

  @Column(name = "event_key", length = 200)
  private String eventKey;

  @Column(name = "projection_version", nullable = false)
  private int projectionVersion;

  @Column(name = "retention_until", nullable = false)
  private Instant retentionUntil;

  @Column(name = "sync_run_id", length = 80)
  private String syncRunId;

  @Column(name = "related_sync_id", length = 200)
  private String relatedSyncId;

  @Column(name = "related_payment_id", length = 200)
  private String relatedPaymentId;

  @Column(name = "related_interaction_id", length = 200)
  private String relatedInteractionId;

  @Column(name = "pages_consulted")
  private Integer pagesConsulted;

  @Column(name = "found_count")
  private Integer foundCount;

  @Column(name = "new_count")
  private Integer newCount;

  @Column(name = "updated_count")
  private Integer updatedCount;

  @Column(name = "ignored_count")
  private Integer ignoredCount;

  @Column(name = "failed_count")
  private Integer failedCount;
}
