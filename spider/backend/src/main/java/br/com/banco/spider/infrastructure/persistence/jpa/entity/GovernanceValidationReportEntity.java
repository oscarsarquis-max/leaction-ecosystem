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
@Table(name = "tb_governance_validation_report")
@Getter
@Setter
@NoArgsConstructor
public class GovernanceValidationReportEntity {

  @Id
  @Column(name = "report_id", length = 120)
  private String reportId;

  @Column(name = "bundle_id", nullable = false, length = 120)
  private String bundleId;

  @Column(name = "validator_version", nullable = false, length = 40)
  private String validatorVersion;

  @Column(nullable = false)
  private boolean passed;

  @Column(name = "error_count", nullable = false)
  private int errorCount;

  @Column(name = "warning_count", nullable = false)
  private int warningCount;

  @Column(name = "info_count", nullable = false)
  private int infoCount;

  @Column(name = "findings_json", columnDefinition = "text")
  private String findingsJson;

  @Column(name = "created_at", nullable = false)
  private Instant createdAt;

  @Column(name = "created_by_principal", nullable = false, length = 200)
  private String createdByPrincipal;
}
