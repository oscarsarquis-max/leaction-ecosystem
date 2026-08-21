package br.com.banco.spider.execution.signal.protection;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/** Retention invocável — sem scheduler. */
@Service
public class ProtectedSignalEnvelopeRetentionService {

  private static final Logger log =
      LoggerFactory.getLogger(ProtectedSignalEnvelopeRetentionService.class);

  private final ProtectedSignalEnvelopeStorePort store;
  private final boolean enabled;
  private final int batchSize;
  private final Duration safetyWindow;

  public ProtectedSignalEnvelopeRetentionService(
      ProtectedSignalEnvelopeStorePort store,
      @Value("${spider.signal.envelope-protection.retention-enabled:false}") boolean enabled,
      @Value("${spider.signal.envelope-protection.retention-batch-size:100}") int batchSize) {
    this.store = store;
    this.enabled = enabled;
    this.batchSize = Math.max(1, Math.min(batchSize, 500));
    this.safetyWindow = Duration.ofHours(24);
  }

  public int markEligible(Instant now) {
    if (!enabled) {
      return 0;
    }
    List<ProtectedSignalEnvelope> consumed = store.findByState(ProtectedEnvelopeState.CONSUMED);
    int marked = 0;
    for (ProtectedSignalEnvelope e : consumed) {
      if (marked >= batchSize) {
        break;
      }
      if (e.consumedAt() != null && e.consumedAt().plus(safetyWindow).isBefore(now)) {
        store.updateState(
            e.inboxLogicalKey(),
            e.optimisticVersion(),
            ProtectedEnvelopeState.DELETION_ELIGIBLE,
            null,
            null,
            e.consumedAt(),
            now);
        marked++;
        log.info("event=retention_eligible reasonCode=OK");
      }
    }
    return marked;
  }

  public int tombstoneEligible(Instant now) {
    if (!enabled) {
      return 0;
    }
    List<ProtectedSignalEnvelope> eligible =
        store.findByState(ProtectedEnvelopeState.DELETION_ELIGIBLE);
    int n = 0;
    for (ProtectedSignalEnvelope e : eligible) {
      if (n >= batchSize) {
        break;
      }
      store.updateState(
          e.inboxLogicalKey(),
          e.optimisticVersion(),
          ProtectedEnvelopeState.DELETED_TOMBSTONE,
          null,
          null,
          e.consumedAt(),
          e.eligibleForDeletionAt());
      n++;
      log.info("event=retention_tombstoned reasonCode=OK");
    }
    return n;
  }
}
