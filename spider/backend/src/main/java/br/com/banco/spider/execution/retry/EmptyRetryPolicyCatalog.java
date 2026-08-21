package br.com.banco.spider.execution.retry;

import java.util.Optional;

public class EmptyRetryPolicyCatalog implements RetryPolicyCatalogPort {
  @Override
  public Optional<RetryPolicyDefinition> findPublished(String policyCode, String version) {
    return Optional.empty();
  }

  @Override
  public Optional<RetryPolicyDefinition> findByRef(String policyRef) {
    return Optional.empty();
  }
}
