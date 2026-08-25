package br.com.banco.spider.operational.workers.handlers;

import br.com.banco.spider.execution.callback.CallbackOutboxProcessor;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import java.time.Instant;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

public class CallbackDeliveryWorkerHandler implements WorkerTypeHandler {

  private final CallbackOutboxProcessor processor;

  public CallbackDeliveryWorkerHandler(CallbackOutboxProcessor processor) {
    this.processor = processor;
  }

  @Override
  public WorkerType workerType() {
    return WorkerType.CALLBACK_DELIVERY;
  }

  @Override
  public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
    return processor
        .findReady(now, batchSize)
        .flatMap(
            ready -> {
              if (ready.isEmpty()) {
                return Mono.just(ScheduleOutcome.SKIPPED);
              }
              return Flux.fromIterable(ready)
                  .concatMap(
                      record ->
                          processor
                              .process(record.outboxId(), record.stateVersion())
                              .map(processed -> Boolean.TRUE)
                              .onErrorReturn(Boolean.FALSE))
                  .collectList()
                  .map(
                      outcomes -> {
                        long dispatched =
                            outcomes.stream().filter(Boolean::booleanValue).count();
                        if (dispatched == 0) {
                          return ScheduleOutcome.PARTIAL;
                        }
                        return dispatched == outcomes.size()
                            ? ScheduleOutcome.SUCCESS
                            : ScheduleOutcome.PARTIAL;
                      });
            });
  }
}
