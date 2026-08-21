package br.com.banco.spider.execution.callback;

import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class ConfiguredCallbackReconciliationPolicyCatalog
    implements CallbackReconciliationPolicyCatalogPort {

  private final Map<String, CallbackReconciliationPolicy> byRef;

  public ConfiguredCallbackReconciliationPolicyCatalog(
      List<CallbackReconciliationPolicy> policies) {
    Map<String, CallbackReconciliationPolicy> map = new java.util.LinkedHashMap<>();
    for (CallbackReconciliationPolicy p :
        policies == null ? List.<CallbackReconciliationPolicy>of() : policies) {
      map.put(p.exactRef(), p);
    }
    this.byRef = Map.copyOf(map);
  }

  @Override
  public Optional<CallbackReconciliationPolicy> findByExactRef(String exactRef) {
    return Optional.ofNullable(byRef.get(exactRef));
  }
}
