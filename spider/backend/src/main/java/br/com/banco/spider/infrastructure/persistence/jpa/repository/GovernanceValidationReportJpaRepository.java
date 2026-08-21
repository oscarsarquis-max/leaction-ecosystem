package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceValidationReportEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceValidationReportJpaRepository
    extends JpaRepository<GovernanceValidationReportEntity, String> {

  Optional<GovernanceValidationReportEntity> findFirstByBundleIdOrderByCreatedAtDesc(
      String bundleId);
}
