package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.Version;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_governance_activation")
@Getter
@Setter
@NoArgsConstructor
public class GovernanceActivationEntity {

  @Id
  @Column(name = "governance_scope", length = 64)
  private String governanceScope;

  @Column(name = "active_snapshot_id", nullable = false, length = 120)
  private String activeSnapshotId;

  @Column(name = "previous_snapshot_id", length = 120)
  private String previousSnapshotId;

  @Column(name = "activation_sequence", nullable = false)
  private long activationSequence;

  @Column(name = "activated_at", nullable = false)
  private Instant activatedAt;

  @Column(name = "activated_by_principal", nullable = false, length = 200)
  private String activatedByPrincipal;

  @Column(name = "reason_code", nullable = false, length = 80)
  private String reasonCode;

  @Version
  @Column(nullable = false)
  private long version;
}
