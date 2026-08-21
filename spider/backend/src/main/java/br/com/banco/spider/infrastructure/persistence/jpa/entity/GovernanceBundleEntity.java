package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.governance.GovernanceLifecycleState;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import jakarta.persistence.Version;
import java.time.Instant;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
    name = "tb_governance_bundle",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_tb_governance_bundle_ref",
            columnNames = {"bundle_code", "bundle_version", "governance_scope"}))
@Getter
@Setter
@NoArgsConstructor
public class GovernanceBundleEntity {

  @Id
  @Column(name = "bundle_id", length = 120)
  private String bundleId;

  @Column(name = "bundle_code", nullable = false, length = 120)
  private String bundleCode;

  @Column(name = "bundle_version", nullable = false, length = 40)
  private String bundleVersion;

  @Column(name = "governance_scope", nullable = false, length = 64)
  private String governanceScope;

  @Column(name = "bundle_digest", nullable = false, length = 128)
  private String bundleDigest;

  @Enumerated(EnumType.STRING)
  @Column(name = "lifecycle_state", nullable = false, length = 40)
  private GovernanceLifecycleState lifecycleState;

  @Column(name = "validation_report_ref", length = 120)
  private String validationReportRef;

  @Column(name = "created_by_principal", nullable = false, length = 200)
  private String createdByPrincipal;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "validated_at")
  private Instant validatedAt;

  @Column(name = "published_at")
  private Instant publishedAt;

  @Column(name = "deprecated_at")
  private Instant deprecatedAt;

  @Column(name = "retired_at")
  private Instant retiredAt;

  @Column(name = "revoked_at")
  private Instant revokedAt;

  @Column(name = "reason_code", length = 80)
  private String reasonCode;

  @Version
  @Column(nullable = false)
  private long version;
}
