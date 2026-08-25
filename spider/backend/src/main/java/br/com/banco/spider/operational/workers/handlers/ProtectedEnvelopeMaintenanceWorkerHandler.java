package br.com.banco.spider.operational.workers.handlers;

import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeRetentionService;
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import br.com.banco.spider.operational.workers.WorkerTypeHandler;
import java.time.Instant;
import org.springframework.beans.factory.ObjectProvider;
import reactor.core.publisher.Mono;

/**
 * Manutenção de envelopes protegidos. O serviço de retenção só existe em algumas configurações; a
 * ausência dele é silenciosa e o ciclo é apenas ignorado.
 */
public class ProtectedEnvelopeMaintenanceWorkerHandler implements WorkerTypeHandler {

  private final ObjectProvider<ProtectedSignalEnvelopeRetentionService> retentionProvider;

  public ProtectedEnvelopeMaintenanceWorkerHandler(
      ObjectProvider<ProtectedSignalEnvelopeRetentionService> retentionProvider) {
    this.retentionProvider = retentionProvider;
  }

  @Override
  public WorkerType workerType() {
    return WorkerType.PROTECTED_ENVELOPE_MAINTENANCE;
  }

  @Override
  public Mono<ScheduleOutcome> execute(String workerId, int batchSize, Instant now) {
    return Mono.fromCallable(
        () -> {
          ProtectedSignalEnvelopeRetentionService retention = retentionProvider.getIfAvailable();
          if (retention == null) {
            return ScheduleOutcome.SKIPPED;
          }
          int marked = retention.markEligible(now);
          int tombstoned = retention.tombstoneEligible(now);
          return marked + tombstoned == 0 ? ScheduleOutcome.SKIPPED : ScheduleOutcome.SUCCESS;
        });
  }
}
