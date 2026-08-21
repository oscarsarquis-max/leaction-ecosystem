package br.com.banco.spider.governance;

import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record GovernanceValidationReport(
    String reportId,
    String bundleId,
    String validatorVersion,
    boolean passed,
    int errorCount,
    int warningCount,
    int infoCount,
    List<GovernanceValidationFinding> findings,
    Instant createdAt,
    String createdByPrincipalRef) {

  public GovernanceValidationReport {
    Objects.requireNonNull(reportId, "reportId");
    Objects.requireNonNull(bundleId, "bundleId");
    Objects.requireNonNull(validatorVersion, "validatorVersion");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(createdByPrincipalRef, "createdByPrincipalRef");
    findings = findings == null ? List.of() : List.copyOf(findings);
  }
}
