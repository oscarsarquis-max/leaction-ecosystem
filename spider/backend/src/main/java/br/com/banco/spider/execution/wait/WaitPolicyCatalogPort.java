package br.com.banco.spider.execution.wait;

import java.util.Optional;

public interface WaitPolicyCatalogPort {
  Optional<WaitPolicyDefinition> findPublished(String policyCode, String version);

  Optional<WaitPolicyDefinition> findByRef(String policyRef);
}
