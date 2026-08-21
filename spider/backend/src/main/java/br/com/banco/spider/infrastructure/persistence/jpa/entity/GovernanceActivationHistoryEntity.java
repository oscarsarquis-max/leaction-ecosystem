package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
    name = "tb_governance_activation_history",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_tb_governance_activation_history_scope_sequence",
            columnNames = {"governance_scope", "activation_sequence"}))
@Getter
@Setter
@NoArgsConstructor
public class GovernanceActivationHistoryEntity {

  @Id
  @GeneratedValue(strategy = GenerationType.IDENTITY)
  @Column(name = "history_id")
  private Long historyId;

  @Column(name = "governance_scope", nullable = false, length = 64)
  private String governanceScope;

  @Column(name = "activation_sequence", nullable = false)
  private long activationSequence;

  @Column(name = "active_snapshot_id", nullable = false, length = 120)
  private String activeSnapshotId;

  @Column(name = "previous_snapshot_id", length = 120)
  private String previousSnapshotId;

  @Column(name = "activated_at", nullable = false)
  private Instant activatedAt;

  @Column(name = "activated_by_principal", nullable = false, length = 200)
  private String activatedByPrincipal;

  @Column(name = "reason_code", nullable = false, length = 80)
  private String reasonCode;
}
