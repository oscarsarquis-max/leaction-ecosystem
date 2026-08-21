package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_execution_control")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionControlEntity {

  @Id
  @Column(name = "execution_id", length = 120)
  private String executionId;

  @Column(name = "context_id", nullable = false, length = 120)
  private String contextId;

  @Column(name = "correlation_id", nullable = false, length = 200)
  private String correlationId;

  @Column(name = "plan_id", length = 120)
  private String planId;

  @Column(name = "route_code", length = 120)
  private String routeCode;

  @Column(name = "route_version", length = 40)
  private String routeVersion;

  @Enumerated(EnumType.STRING)
  @Column(nullable = false, length = 40)
  private ExecutionState state;

  @Column(name = "state_version", nullable = false)
  private long stateVersion;

  @Enumerated(EnumType.STRING)
  @Column(name = "technical_status", length = 40)
  private TechnicalStatus technicalStatus;

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "completed_at")
  private Instant completedAt;

  @Column(name = "last_updated_at", nullable = false)
  private Instant lastUpdatedAt;

  @Column(name = "active_wait_type", length = 80)
  private String activeWaitType;

  @Column(name = "retention_class_ref", nullable = false, length = 120)
  private String retentionClassRef;

  @Column(name = "owner_principal_ref", length = 200)
  private String ownerPrincipalRef;
}
