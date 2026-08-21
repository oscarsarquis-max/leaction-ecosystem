package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.governance.GovernanceArtifactType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.IdClass;
import jakarta.persistence.Table;
import jakarta.persistence.UniqueConstraint;
import java.io.Serializable;
import lombok.EqualsAndHashCode;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.Setter;

@Entity
@Table(
    name = "tb_governance_bundle_artifact",
    uniqueConstraints =
        @UniqueConstraint(
            name = "uq_tb_governance_bundle_artifact",
            columnNames = {"bundle_id", "artifact_type", "artifact_code", "artifact_version"}))
@IdClass(GovernanceBundleArtifactEntity.BundleArtifactId.class)
@Getter
@Setter
@NoArgsConstructor
public class GovernanceBundleArtifactEntity {

  @Id
  @Column(name = "bundle_id", length = 120)
  private String bundleId;

  @Id
  @Enumerated(EnumType.STRING)
  @Column(name = "artifact_type", length = 80)
  private GovernanceArtifactType artifactType;

  @Id
  @Column(name = "artifact_code", length = 120)
  private String artifactCode;

  @Id
  @Column(name = "artifact_version", length = 40)
  private String artifactVersion;

  @Column(name = "ordinal_pos", nullable = false)
  private int ordinalPos;

  @Getter
  @Setter
  @NoArgsConstructor
  @EqualsAndHashCode
  public static class BundleArtifactId implements Serializable {
    private String bundleId;
    private GovernanceArtifactType artifactType;
    private String artifactCode;
    private String artifactVersion;
  }
}
