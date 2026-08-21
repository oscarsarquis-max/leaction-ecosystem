package br.com.banco.spider.execution.wait;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import java.util.stream.Collectors;

public final class ConfiguredWaitPolicyCatalog implements WaitPolicyCatalogPort {

  private final Map<String, WaitPolicyDefinition> byRef;

  public ConfiguredWaitPolicyCatalog(List<WaitPolicyDefinition> policies) {
    this.byRef =
        policies.stream()
            .filter(p -> p.status().isEligible())
            .collect(Collectors.toUnmodifiableMap(WaitPolicyDefinition::ref, Function.identity()));
  }

  @Override
  public Optional<WaitPolicyDefinition> findPublished(String policyCode, String version) {
    return findByRef("policy:wait:" + policyCode + "@" + version);
  }

  @Override
  public Optional<WaitPolicyDefinition> findByRef(String policyRef) {
    if (policyRef == null || policyRef.isBlank()) {
      return Optional.empty();
    }
    return Optional.ofNullable(byRef.get(policyRef.trim()));
  }
}
