package br.com.banco.spider.execution.callback;

import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/** Recovery invocável de leases expirados (dispatch + reconciliation). Sem scheduler. */
@Service
public class CallbackProcessingRecoveryService {

  private static final Logger log = LoggerFactory.getLogger(CallbackProcessingRecoveryService.class);

  public record RecoverySummary(
      int outboxRecovered, int reconciliationRecovered, int expired, int manualReview) {}

  private final CallbackReconciliationStorePort reconciliationStore;
  private final CallbackOutboxProcessor outboxProcessor;
  private final SpiderClock clock;

  public CallbackProcessingRecoveryService(
      CallbackOutboxStorePort outboxStore,
      CallbackReconciliationStorePort reconciliationStore,
      CallbackOutboxProcessor outboxProcessor,
      SpiderClock clock) {
    this.reconciliationStore = reconciliationStore;
    this.outboxProcessor = outboxProcessor;
    this.clock = clock;
  }

  public Mono<RecoverySummary> recover(Instant now) {
    return outboxProcessor
        .recoverInterruptedDispatches(now)
        .map(
            outboxCount -> {
              int recon = 0;
              int expired = 0;
              int manual = 0;
              List<CallbackReconciliationRecord> leases =
                  reconciliationStore.findExpiredLeases(now);
              for (CallbackReconciliationRecord r : leases) {
                log.info(
                    "event=expired_lease_recovered reconciliationId={} reasonCode=LEASE_EXPIRED",
                    r.reconciliationId());
                if (!r.expiresAt().isAfter(now)) {
                  reconciliationStore.update(
                      r.reconciliationId(),
                      r.version(),
                      CallbackReconciliationState.EXPIRED,
                      r.queryCount(),
                      r.nextQueryAt(),
                      r.lastDisposition(),
                      null,
                      null,
                      null,
                      now);
                  expired++;
                  continue;
                }
                // Query may have started — schedule safe retry without inventing success
                reconciliationStore.update(
                    r.reconciliationId(),
                    r.version(),
                    CallbackReconciliationState.RETRY_SCHEDULED,
                    r.queryCount(),
                    now,
                    CallbackDeliveryStatusDisposition.UNKNOWN,
                    null,
                    null,
                    null,
                    now);
                recon++;
              }
              return new RecoverySummary(outboxCount, recon, expired, manual);
            });
  }
}
