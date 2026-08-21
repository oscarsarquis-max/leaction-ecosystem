package br.com.banco.spider.execution.retry;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

/** Catálogo imutável para testes/dev — não é Control Plane. */
public final class ConfiguredRetryPolicyCatalog implements RetryPolicyCatalogPort {

  private final Map<String, RetryPolicyDefinition> byRef;

  public ConfiguredRetryPolicyCatalog(List<RetryPolicyDefinition> policies) {
    this.byRef =
        policies.stream()
            .filter(p -> p.status().isEligible())
            .collect(Collectors.toUnmodifiableMap(RetryPolicyDefinition::ref, Function.identity()));
  }

  @Override
  public Optional<RetryPolicyDefinition> findPublished(String policyCode, String version) {
    return findByRef("policy:retry:" + policyCode + "@" + version);
  }

  @Override
  public Optional<RetryPolicyDefinition> findByRef(String policyRef) {
    if (policyRef == null || policyRef.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(byRef.get(policyRef.trim()));
  }
}
