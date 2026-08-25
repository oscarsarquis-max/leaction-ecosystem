package br.com.banco.spider.operational.workers.handlers;

import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitExpiryProcessor;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import java.time.Instant;
import java.util.List;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

public class WaitExpiryWorkerHandler implements WorkerTypeHandler {

  private final WaitExpiryProcessor processor;

  public WaitExpiryWorkerHandler(WaitExpiryProcessor processor) {
    this.processor = processor;
  }

  @Override
  public WorkerType workerType() {
    return WorkerType.WAIT_EXPIRY;
  }

  @Override
  public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
    return Mono.fromCallable(processor::findExpiredWaiting)
        .flatMap(
            expired -> {
              if (expired.isEmpty()) {
                return Mono.just(ScheduleOutcome.SKIPPED);
              }
              List<ExecutionWaitRecord> batch = expired.stream().limit(batchSize).toList();
              return Flux.fromIterable(batch)
                  .concatMap(
                      wait ->
                          processor
                              .expire(wait.waitId(), wait.stateVersion())
                              .onErrorReturn(Boolean.FALSE))
                  .collectList()
                  .map(
                      outcomes -> {
                        long expiredCount = outcomes.stream().filter(Boolean::booleanValue).count();
                        if (expiredCount == 0) {
                          return ScheduleOutcome.PARTIAL;
                        }
                        return expiredCount == outcomes.size()
                            ? ScheduleOutcome.SUCCESS
                            : ScheduleOutcome.PARTIAL;
                      });
            });
  }
}
