package br.com.banco.spider.security.replay;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

/** Cleanup invocável — sem scheduler. */
public class ReplayGuardCleanupService {

  private static final Logger log = LoggerFactory.getLogger(ReplayGuardCleanupService.class);

  private final ReplayGuardPort replayGuard;

  public ReplayGuardCleanupService(ReplayGuardPort replayGuard) {
    this.replayGuard = replayGuard;
  }

  public int cleanup(java.time.Instant now, int batchSize) {
    int limit = Math.min(Math.max(batchSize, 1), 500);
    int removed = replayGuard.cleanupExpired(now, limit);
    log.info("event=replay_cleanup_count removed={} batchSize={}", removed, limit);
    return removed;
  }
}
