package br.com.banco.spider.execution.callback;

import java.util.Optional;
import reactor.core.publisher.Mono;

public interface CallbackBindingResolverPort {
  Mono<Optional<CallbackDeliveryPort>> resolve(String bindingRef);
}
