package br.com.banco.spider.operational.workers.handlers;

import br.com.banco.spider.execution.callback.CallbackProcessingRecoveryService;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import java.time.Instant;
import reactor.core.publisher.Mono;

public class CallbackRecoveryWorkerHandler implements WorkerTypeHandler {

  private final CallbackProcessingRecoveryService recoveryService;

  public CallbackRecoveryWorkerHandler(CallbackProcessingRecoveryService recoveryService) {
    this.recoveryService = recoveryService;
  }

  @Override
  public WorkerType workerType() {
    return WorkerType.CALLBACK_RECOVERY;
  }

  @Override
  public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
    return recoveryService
        .recover(now)
        .map(
            summary -> {
              int touched =
                  summary.outboxRecovered()
                      + summary.reconciliationRecovered()
                      + summary.expired()
                      + summary.manualReview();
              return touched == 0 ? ScheduleOutcome.SKIPPED : ScheduleOutcome.SUCCESS;
            });
  }
}
