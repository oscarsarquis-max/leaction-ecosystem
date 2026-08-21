package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.security.replay.ReplayDecision;
import br.com.banco.spider.security.replay.ReplayDecisionStatus;
import br.com.banco.spider.security.replay.ReplayGuardPort;
import br.com.banco.spider.security.replay.ReplayReservation;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryReplayGuardAdapter implements ReplayGuardPort {

  private final Map<String, ReplayReservation> byScopeNonce = new ConcurrentHashMap<>();

  private static String key(String scope, String nonceHash, String version) {
    return scope + "|" + nonceHash + "|" + version;
  }

  @Override
  public synchronized ReplayDecision reserve(ReplayReservation candidate) {
    if (!candidate.expiresAt().isAfter(candidate.firstSeenAt())) {
      return new ReplayDecision(ReplayDecisionStatus.EXPIRED_PROOF, candidate);
    }
    String k =
        key(candidate.replayScopeHash(), candidate.nonceHash(), candidate.fingerprintVersion());
    ReplayReservation existing = byScopeNonce.get(k);
    if (existing == null) {
      ReplayReservation stored =
          new ReplayReservation(
              candidate.reservationId(),
              candidate.replayScopeHash(),
              candidate.nonceHash(),
              candidate.messageFingerprint(),
              candidate.fingerprintVersion(),
              candidate.keyRef(),
              candidate.keyVersion(),
              candidate.integrityProfileRef(),
              candidate.firstSeenAt(),
              candidate.expiresAt(),
              ReplayDecisionStatus.RESERVED,
              0L);
      byScopeNonce.put(k, stored);
      return new ReplayDecision(ReplayDecisionStatus.RESERVED, stored);
    }
    if (existing.messageFingerprint().equals(candidate.messageFingerprint())) {
      return new ReplayDecision(ReplayDecisionStatus.DUPLICATE_SAME_MESSAGE, existing);
    }
    return new ReplayDecision(ReplayDecisionStatus.REPLAY_CONFLICT, existing);
  }

  @Override
  public synchronized int cleanupExpired(Instant now, int batchSize) {
    int removed = 0;
    List<Map.Entry<String, ReplayReservation>> expired = new ArrayList<>();
    for (Map.Entry<String, ReplayReservation> e : byScopeNonce.entrySet()) {
      if (!e.getValue().expiresAt().isAfter(now)) {
        expired.add(e);
      }
    }
    expired.sort(Comparator.comparing(e -> e.getValue().expiresAt()));
    Iterator<Map.Entry<String, ReplayReservation>> it = expired.iterator();
    while (it.hasNext() && removed < batchSize) {
      byScopeNonce.remove(it.next().getKey());
      removed++;
    }
    return removed;
  }

  public void clear() {
    byScopeNonce.clear();
  }

  public int size() {
    return byScopeNonce.size();
  }
}
