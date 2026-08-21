package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceBundleEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceBundleJpaRepository
    extends JpaRepository<GovernanceBundleEntity, String> {

  Optional<GovernanceBundleEntity> findByBundleCodeAndBundleVersionAndGovernanceScope(
      String bundleCode, String bundleVersion, String governanceScope);
}
