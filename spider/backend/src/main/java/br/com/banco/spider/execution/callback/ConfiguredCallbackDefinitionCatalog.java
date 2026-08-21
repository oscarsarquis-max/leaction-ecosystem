package br.com.banco.spider.execution.callback;

import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class ConfiguredCallbackDefinitionCatalog implements CallbackDefinitionCatalogPort {

  private final Map<String, CallbackDefinition> byRef;

  public ConfiguredCallbackDefinitionCatalog(List<CallbackDefinition> definitions) {
    Map<String, CallbackDefinition> map = new java.util.LinkedHashMap<>();
    for (CallbackDefinition d : definitions == null ? List.<CallbackDefinition>of() : definitions) {
      map.put(d.exactRef(), d);
    }
    this.byRef = Map.copyOf(map);
  }

  @Override
  public Optional<CallbackDefinition> findByExactRef(String exactRef) {
    return Optional.ofNullable(byRef.get(exactRef));
  }

  @Override
  public List<CallbackDefinition> allPublished() {
    return byRef.values().stream().filter(CallbackDefinition::isEligible).toList();
  }
}
