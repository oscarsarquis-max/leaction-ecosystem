package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.governance.GovernanceArtifactType;
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
    name = "tb_governance_artifact",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_tb_governance_artifact_ref",
            columnNames = {"artifact_type", "artifact_code", "artifact_version"}))
@Getter
@Setter
@NoArgsConstructor
public class GovernanceArtifactEntity {

  @Id
  @Column(name = "artifact_id", length = 120)
  private String artifactId;

  @Enumerated(EnumType.STRING)
  @Column(name = "artifact_type", nullable = false, length = 80)
  private GovernanceArtifactType artifactType;

  @Column(name = "artifact_code", nullable = false, length = 120)
  private String artifactCode;

  @Column(name = "artifact_version", nullable = false, length = 40)
  private String artifactVersion;

  @Column(name = "schema_version", nullable = false, length = 40)
  private String schemaVersion;

  @Column(name = "canonical_content", nullable = false, columnDefinition = "text")
  private String canonicalContent;

  @Column(name = "content_digest", nullable = false, length = 128)
  private String contentDigest;

  @Enumerated(EnumType.STRING)
  @Column(name = "lifecycle_state", nullable = false, length = 40)
  private GovernanceLifecycleState lifecycleState;

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

  @Column(name = "lifecycle_reason_code", length = 80)
  private String lifecycleReasonCode;

  @Version
  @Column(nullable = false)
  private long version;
}
