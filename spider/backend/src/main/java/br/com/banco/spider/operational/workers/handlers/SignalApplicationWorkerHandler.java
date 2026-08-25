package br.com.banco.spider.operational.workers.handlers;

import br.com.banco.spider.execution.signal.ExternalSignalApplicationProcessor;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import java.time.Instant;
import reactor.core.publisher.Mono;

public class SignalApplicationWorkerHandler implements WorkerTypeHandler {

  private final ExternalSignalApplicationProcessor processor;

  public SignalApplicationWorkerHandler(ExternalSignalApplicationProcessor processor) {
    this.processor = processor;
  }

  @Override
  public WorkerType workerType() {
    return WorkerType.SIGNAL_APPLICATION;
  }

  @Override
  public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
    return processor
        .processPending(workerId, now, batchSize)
        .map(
            result -> {
              if (result.claimed() == 0) {
                return ScheduleOutcome.SKIPPED;
              }
              return result.manual() > 0 ? ScheduleOutcome.PARTIAL : ScheduleOutcome.SUCCESS;
            });
  }
}
