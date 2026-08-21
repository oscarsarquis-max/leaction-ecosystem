package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceSnapshotEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceSnapshotJpaRepository
    extends JpaRepository<GovernanceSnapshotEntity, String> {

  Optional<GovernanceSnapshotEntity> findByBundleRefAndBundleDigest(
      String bundleRef, String bundleDigest);
}
