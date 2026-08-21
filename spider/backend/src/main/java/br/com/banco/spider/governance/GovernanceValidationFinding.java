package br.com.banco.spider.governance;

import java.util.Objects;

public record GovernanceValidationFinding(
    GovernanceValidationCategory category,
    GovernanceValidationSeverity severity,
    String reasonCode,
    String message,
    String targetRef) {

  public GovernanceValidationFinding {
    Objects.requireNonNull(category, "category");
    Objects.requireNonNull(severity, "severity");
    Objects.requireNonNull(reasonCode, "reasonCode");
    Objects.requireNonNull(message, "message");
  }
}
