package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.GovernanceArtifact;
import br.com.banco.spider.governance.GovernanceArtifactRef;
import br.com.banco.spider.governance.GovernanceArtifactType;
import java.util.List;
import java.util.Optional;

public interface GovernanceArtifactStorePort {
  GovernanceArtifact insert(GovernanceArtifact artifact);

  Optional<GovernanceArtifact> findArtifactById(String artifactId);

  Optional<GovernanceArtifact> findByRef(GovernanceArtifactRef ref);

  Optional<GovernanceArtifact> findByTypeCodeVersion(
      GovernanceArtifactType type, String code, String version);

  GovernanceArtifact update(GovernanceArtifact artifact);

  List<GovernanceArtifact> findByIds(List<String> artifactIds);
}
