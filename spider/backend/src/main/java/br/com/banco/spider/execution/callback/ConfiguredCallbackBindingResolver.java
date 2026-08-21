package br.com.banco.spider.execution.callback;

import java.util.Map;
import java.util.Optional;
import reactor.core.publisher.Mono;

public class ConfiguredCallbackBindingResolver implements CallbackBindingResolverPort {

  private final Map<String, CallbackDeliveryPort> bindings;

  public ConfiguredCallbackBindingResolver(Map<String, CallbackDeliveryPort> bindings) {
    this.bindings = bindings == null ? Map.of() : Map.copyOf(bindings);
  }

  @Override
  public Mono<Optional<CallbackDeliveryPort>> resolve(String bindingRef) {
    if (bindingRef == null || bindingRef.isBlank()) {
      return Mono.just(Optional.empty());
    }
    return Mono.just(Optional.ofNullable(bindings.get(bindingRef.trim())));
  }
}
