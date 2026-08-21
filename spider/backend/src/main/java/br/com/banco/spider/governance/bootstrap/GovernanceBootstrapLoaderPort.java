package br.com.banco.spider.governance.bootstrap;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceScope;

/** Bootstrap Mock — desabilitado por default; não lê path arbitrário nem rede. */
public interface GovernanceBootstrapLoaderPort {
  ActiveGovernanceSnapshot loadAndPublishActivate(
      GovernanceScope scope, String author, String publisher, String activator);
}
