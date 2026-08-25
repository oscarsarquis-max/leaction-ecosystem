package br.com.banco.spider.operational.workers.handlers;

import br.com.banco.spider.execution.callback.CallbackReconciliationProcessor;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import java.time.Instant;
import reactor.core.publisher.Mono;

public class CallbackReconciliationWorkerHandler implements WorkerTypeHandler {

  private final CallbackReconciliationProcessor processor;

  public CallbackReconciliationWorkerHandler(CallbackReconciliationProcessor processor) {
    this.processor = processor;
  }

  @Override
  public WorkerType workerType() {
    return WorkerType.CALLBACK_RECONCILIATION;
  }

  @Override
  public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
    return processor
        .processDue(workerId, now, batchSize)
        .map(
            result -> {
              if (result.claimed() == 0) {
                return ScheduleOutcome.SKIPPED;
              }
              return result.failed() > 0 || result.manualReview() > 0
                  ? ScheduleOutcome.PARTIAL
                  : ScheduleOutcome.SUCCESS;
            });
  }
}
