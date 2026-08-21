package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.governance.GovernanceMode;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(name = "tb_execution_governance_fixation")
@Getter
@Setter
@NoArgsConstructor
public class ExecutionGovernanceFixationEntity {

  @Id
  @Column(name = "execution_id", length = 120)
  private String executionId;

  @Enumerated(EnumType.STRING)
  @Column(name = "governance_mode", nullable = false, length = 40)
  private GovernanceMode governanceMode;

  @Column(name = "governance_scope", nullable = false, length = 64)
  private String governanceScope;

  @Column(name = "snapshot_id", nullable = false, length = 120)
  private String snapshotId;

  @Column(name = "bundle_code", nullable = false, length = 120)
  private String bundleCode;

  @Column(name = "bundle_version", nullable = false, length = 40)
  private String bundleVersion;

  @Column(name = "bundle_digest", nullable = false, length = 128)
  private String bundleDigest;

  @Column(name = "snapshot_digest", nullable = false, length = 128)
  private String snapshotDigest;

  @Column(name = "activation_sequence", nullable = false)
  private long activationSequence;

  @Column(name = "fixed_at", nullable = false)
  private Instant fixedAt;
}
