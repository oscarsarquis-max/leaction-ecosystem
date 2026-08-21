package br.com.banco.spider.execution.callback;

import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class ConfiguredCallbackDeliveryPolicyCatalog
    implements CallbackDeliveryPolicyCatalogPort {

  private final Map<String, CallbackDeliveryPolicy> byRef;

  public ConfiguredCallbackDeliveryPolicyCatalog(List<CallbackDeliveryPolicy> policies) {
    Map<String, CallbackDeliveryPolicy> map = new java.util.LinkedHashMap<>();
    for (CallbackDeliveryPolicy p :
        policies == null ? List.<CallbackDeliveryPolicy>of() : policies) {
      map.put(p.exactRef(), p);
    }
    this.byRef = Map.copyOf(map);
  }

  @Override
  public Optional<CallbackDeliveryPolicy> findByExactRef(String exactRef) {
    return Optional.ofNullable(byRef.get(exactRef));
  }
}
