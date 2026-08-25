package br.com.banco.spider.operational.workers;

import java.time.Instant;
import reactor.core.publisher.Mono;

/**
 * Adaptador entre o agendamento durável e um processador canônico já existente. O handler não
 * decide nada de negócio: apenas invoca o processador com o lote autorizado.
 */
public interface WorkerTypeHandler {

  WorkerType workerType();

  Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now);
}
