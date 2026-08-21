package br.com.banco.spider.infrastructure.persistence.jpa.repository;

import br.com.banco.spider.governance.GovernanceArtifactType;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.GovernanceArtifactEntity;
import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface GovernanceArtifactJpaRepository
    extends JpaRepository<GovernanceArtifactEntity, String> {

  Optional<GovernanceArtifactEntity> findByArtifactTypeAndArtifactCodeAndArtifactVersion(
      GovernanceArtifactType artifactType, String artifactCode, String artifactVersion);
}
