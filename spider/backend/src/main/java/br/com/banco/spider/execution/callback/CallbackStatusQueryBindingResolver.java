package br.com.banco.spider.execution.callback;

import java.util.Optional;
import reactor.core.publisher.Mono;

public interface CallbackStatusQueryBindingResolver {
  Mono<Optional<CallbackDeliveryStatusQueryPort>> resolve(String statusQueryBindingRef);
}
