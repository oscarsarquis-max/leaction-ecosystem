package br.com.banco.spider.execution.callback;

import reactor.core.publisher.Mono;

public interface CallbackDeliveryPort {
  Mono<CallbackDeliveryResult> deliver(CallbackDeliveryEnvelope envelope);
}
