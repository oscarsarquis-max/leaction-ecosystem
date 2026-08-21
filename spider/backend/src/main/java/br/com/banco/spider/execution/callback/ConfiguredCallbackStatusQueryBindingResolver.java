package br.com.banco.spider.execution.callback;

import java.util.Map;
import java.util.Optional;
import reactor.core.publisher.Mono;

public class ConfiguredCallbackStatusQueryBindingResolver
    implements CallbackStatusQueryBindingResolver {

  private final Map<String, CallbackDeliveryStatusQueryPort> bindings;

  public ConfiguredCallbackStatusQueryBindingResolver(
      Map<String, CallbackDeliveryStatusQueryPort> bindings) {
    this.bindings = bindings == null ? Map.of() : Map.copyOf(bindings);
  }

  @Override
  public Mono<Optional<CallbackDeliveryStatusQueryPort>> resolve(String statusQueryBindingRef) {
    if (statusQueryBindingRef == null || statusQueryBindingRef.isBlank()) {
      return Mono.just(Optional.empty());
    }
    return Mono.just(Optional.ofNullable(bindings.get(statusQueryBindingRef.trim())));
  }
}
