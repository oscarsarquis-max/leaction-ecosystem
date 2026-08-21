package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
    name = "tb_governance_snapshot",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_tb_governance_snapshot_bundle",
            columnNames = {"bundle_ref", "bundle_digest"}))
@Getter
@Setter
@NoArgsConstructor
public class GovernanceSnapshotEntity {

  @Id
  @Column(name = "snapshot_id", length = 120)
  private String snapshotId;

  @Column(name = "bundle_ref", nullable = false, length = 200)
  private String bundleRef;

  @Column(name = "bundle_digest", nullable = false, length = 128)
  private String bundleDigest;

  @Column(name = "governance_scope", nullable = false, length = 64)
  private String governanceScope;

  @Column(name = "snapshot_digest", nullable = false, length = 128)
  private String snapshotDigest;

  @Column(name = "compiled_at", nullable = false)
  private Instant compiledAt;

  @Column(name = "snapshot_json", columnDefinition = "text")
  private String snapshotJson;
}
