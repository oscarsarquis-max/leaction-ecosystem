package br.com.banco.spider.execution.signal;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.WaitState;
import java.time.Instant;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

@Service
public class ExternalSignalApplicationRecoveryService {

  private static final Logger log =
      LoggerFactory.getLogger(ExternalSignalApplicationRecoveryService.class);

  public record RecoverySummary(int released, int applied, int manual) {}

  private final InboxStorePort inboxStore;
  private final ExecutionWaitStorePort waitStore;
  private final SpiderClock clock;
  private final boolean enabled;

  public ExternalSignalApplicationRecoveryService(
      InboxStorePort inboxStore,
      ExecutionWaitStorePort waitStore,
      SpiderClock clock,
      @Value("${spider.signal.application.recovery-enabled:false}") boolean enabled) {
    this.inboxStore = inboxStore;
    this.waitStore = waitStore;
    this.clock = clock;
    this.enabled = enabled;
  }

  public Mono<RecoverySummary> recover(Instant now) {
    if (!enabled) {
      return Mono.just(new RecoverySummary(0, 0, 0));
    }
    return Mono.fromCallable(
        () -> {
          int released = 0;
          int applied = 0;
          int manual = 0;
          List<InboxRecord> interrupted =
              inboxStore.findByProcessingState(InboxProcessingState.APPLYING);
          for (InboxRecord r : interrupted) {
            if (r.leaseUntil() != null && r.leaseUntil().isAfter(now)) {
              continue;
            }
            log.info("event=lease_recovered reasonCode=LEASE_EXPIRED");
            boolean waitDone =
                r.waitId() != null
                    && waitStore
                        .findByWaitId(r.waitId())
                        .map(
                            w ->
                                w.state() == WaitState.RESUMED
                                    || w.state() == WaitState.EXPIRED)
                        .orElse(false);
            if (waitDone) {
              inboxStore.updateApplicationState(
                  r.sourceRef(),
                  r.messageId(),
                  r.version(),
                  InboxProcessingState.APPLIED,
                  null,
                  null,
                  now,
                  r.applicationAttemptCount(),
                  "RECOVERED_APPLIED",
                  now,
                  now);
              applied++;
            } else if (r.applicationAttemptCount() <= 0) {
              inboxStore.updateApplicationState(
                  r.sourceRef(),
                  r.messageId(),
                  r.version(),
                  InboxProcessingState.APPLY_PENDING,
                  null,
                  null,
                  now,
                  r.applicationAttemptCount(),
                  "LEASE_RELEASED",
                  null,
                  now);
              released++;
            } else {
              inboxStore.updateApplicationState(
                  r.sourceRef(),
                  r.messageId(),
                  r.version(),
                  InboxProcessingState.MANUAL_REVIEW,
                  null,
                  null,
                  now,
                  r.applicationAttemptCount(),
                  "AMBIGUOUS_APPLYING",
                  null,
                  now);
              manual++;
            }
          }
          return new RecoverySummary(released, applied, manual);
        });
  }
}
