package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceBundleArtifactEntity;
import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceBundleArtifactJpaRepository
    extends JpaRepository<
        GovernanceBundleArtifactEntity, GovernanceBundleArtifactEntity.BundleArtifactId> {

  List<GovernanceBundleArtifactEntity> findByBundleIdOrderByOrdinalPosAsc(String bundleId);
}
