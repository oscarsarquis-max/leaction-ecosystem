package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.GovernanceBundle;
import br.com.banco.spider.governance.GovernanceScope;
import java.util.Optional;

public interface GovernanceBundleStorePort {
  GovernanceBundle insert(GovernanceBundle bundle);

  Optional<GovernanceBundle> findBundleById(String bundleId);

  Optional<GovernanceBundle> findByCodeVersionScope(
      String bundleCode, String bundleVersion, GovernanceScope scope);

  GovernanceBundle update(GovernanceBundle bundle);
}
