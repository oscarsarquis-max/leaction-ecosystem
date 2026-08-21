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
@Table(name = "tb_governance_audit_event")
@Getter
@Setter
@NoArgsConstructor
public class GovernanceAuditEventEntity {

  @Id
  @Column(name = "event_id", length = 120)
  private String eventId;

  @Column(name = "command_type", nullable = false, length = 80)
  private String commandType;

  @Column(name = "target_type", length = 80)
  private String targetType;

  @Column(name = "target_ref", length = 200)
  private String targetRef;

  @Column(name = "actor_principal_ref", nullable = false, length = 200)
  private String actorPrincipalRef;

  @Column(nullable = false, length = 40)
  private String outcome;

  @Column(name = "reason_code", length = 80)
  private String reasonCode;

  @Column(name = "previous_lifecycle_state", length = 40)
  private String previousLifecycleState;

  @Column(name = "new_lifecycle_state", length = 40)
  private String newLifecycleState;

  @Column(name = "occurred_at", nullable = false)
  private Instant occurredAt;

  @Column(name = "correlation_id", length = 200)
  private String correlationId;
}
