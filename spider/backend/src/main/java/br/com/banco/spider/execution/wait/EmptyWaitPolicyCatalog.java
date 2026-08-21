package br.com.banco.spider.execution.wait;

import java.util.Optional;

public class EmptyWaitPolicyCatalog implements WaitPolicyCatalogPort {
  @Override
  public Optional<WaitPolicyDefinition> findPublished(String policyCode, String version) {
    return Optional.empty();
  }

  @Override
  public Optional<WaitPolicyDefinition> findByRef(String policyRef) {
    return Optional.empty();
  }
}
