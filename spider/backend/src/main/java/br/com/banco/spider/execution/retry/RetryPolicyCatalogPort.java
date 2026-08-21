package br.com.banco.spider.execution.retry;

import java.util.Optional;

public interface RetryPolicyCatalogPort {
  Optional<RetryPolicyDefinition> findPublished(String policyCode, String version);

  Optional<RetryPolicyDefinition> findByRef(String policyRef);
}
