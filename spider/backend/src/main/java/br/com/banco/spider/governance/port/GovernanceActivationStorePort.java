package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.GovernanceActivation;
import br.com.banco.spider.governance.GovernanceScope;
import java.util.Optional;

public interface GovernanceActivationStorePort {
  Optional<GovernanceActivation> findActive(GovernanceScope scope);

  /** Compare-and-set. Retorna empty se perdeu a disputa. */
  Optional<GovernanceActivation> activate(GovernanceActivation activation, long expectedVersion);
}
