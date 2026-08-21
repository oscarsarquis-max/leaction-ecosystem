package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.GovernanceValidationReport;
import java.util.Optional;

public interface GovernanceValidationReportStorePort {
  GovernanceValidationReport insert(GovernanceValidationReport report);

  Optional<GovernanceValidationReport> findReportById(String reportId);

  Optional<GovernanceValidationReport> findLatestByBundleId(String bundleId);
}
