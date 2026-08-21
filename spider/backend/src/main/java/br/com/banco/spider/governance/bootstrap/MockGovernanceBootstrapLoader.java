package br.com.banco.spider.governance.bootstrap;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceScope;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(name = "spider.governance.bootstrap.enabled", havingValue = "true")
public class MockGovernanceBootstrapLoader implements GovernanceBootstrapLoaderPort {

  @Override
  public ActiveGovernanceSnapshot loadAndPublishActivate(
      GovernanceScope scope, String author, String publisher, String activator) {
    throw new UnsupportedOperationException(
        "Bootstrap must go through GovernanceControlPlaneService use cases; wire in tests only");
  }
}
