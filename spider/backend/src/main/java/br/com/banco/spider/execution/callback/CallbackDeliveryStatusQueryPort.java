package br.com.banco.spider.execution.callback;

import reactor.core.publisher.Mono;

public interface CallbackDeliveryStatusQueryPort {
  Mono<CallbackDeliveryStatusQueryResult> query(CallbackDeliveryStatusQuery query);
}
