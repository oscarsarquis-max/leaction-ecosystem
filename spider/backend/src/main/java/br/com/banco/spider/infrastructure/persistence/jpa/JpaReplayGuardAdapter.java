package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.security.replay.ReplayDecision;
import br.com.banco.spider.security.replay.ReplayDecisionStatus;
import br.com.banco.spider.security.replay.ReplayGuardPort;
import br.com.banco.spider.security.replay.ReplayReservation;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.SecurityReplayGuardEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.SecurityReplayGuardJpaRepository;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaReplayGuardAdapter implements ReplayGuardPort {

  private final SecurityReplayGuardJpaRepository repo;

  public JpaReplayGuardAdapter(SecurityReplayGuardJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public ReplayDecision reserve(ReplayReservation candidate) {
    if (!candidate.expiresAt().isAfter(candidate.firstSeenAt())) {
      return new ReplayDecision(ReplayDecisionStatus.EXPIRED_PROOF, candidate);
    }
    Optional<SecurityReplayGuardEntity> existing =
        repo.findByReplayScopeHashAndNonceHashAndFingerprintVersion(
            candidate.replayScopeHash(),
            candidate.nonceHash(),
            candidate.fingerprintVersion());
    if (existing.isPresent()) {
      SecurityReplayGuardEntity e = existing.get();
      if (e.getMessageFingerprint().equals(candidate.messageFingerprint())) {
        return new ReplayDecision(ReplayDecisionStatus.DUPLICATE_SAME_MESSAGE, toModel(e));
      }
      return new ReplayDecision(ReplayDecisionStatus.REPLAY_CONFLICT, toModel(e));
    }
    try {
      SecurityReplayGuardEntity e = toEntity(candidate);
      e.setStatus(ReplayDecisionStatus.RESERVED.name());
      e.setCreatedAt(candidate.firstSeenAt());
      e.setUpdatedAt(candidate.firstSeenAt());
      return new ReplayDecision(ReplayDecisionStatus.RESERVED, toModel(repo.save(e)));
    } catch (DataIntegrityViolationException ex) {
      return repo.findByReplayScopeHashAndNonceHashAndFingerprintVersion(
              candidate.replayScopeHash(),
              candidate.nonceHash(),
              candidate.fingerprintVersion())
          .map(
              e -> {
                if (e.getMessageFingerprint().equals(candidate.messageFingerprint())) {
                  return new ReplayDecision(ReplayDecisionStatus.DUPLICATE_SAME_MESSAGE, toModel(e));
                }
                return new ReplayDecision(ReplayDecisionStatus.REPLAY_CONFLICT, toModel(e));
              })
          .orElse(new ReplayDecision(ReplayDecisionStatus.CAPACITY_REJECTED, candidate));
    }
  }

  @Override
  @Transactional
  public int cleanupExpired(Instant now, int batchSize) {
    List<SecurityReplayGuardEntity> expired = repo.findExpired(now);
    int removed = 0;
    for (SecurityReplayGuardEntity e : expired) {
      if (removed >= batchSize) {
        break;
      }
      repo.delete(e);
      removed++;
    }
    return removed;
  }

  private static SecurityReplayGuardEntity toEntity(ReplayReservation r) {
    SecurityReplayGuardEntity e = new SecurityReplayGuardEntity();
    e.setReservationId(r.reservationId());
    e.setReplayScopeHash(r.replayScopeHash());
    e.setNonceHash(r.nonceHash());
    e.setMessageFingerprint(r.messageFingerprint());
    e.setFingerprintVersion(r.fingerprintVersion());
    e.setKeyRef(r.keyRef());
    e.setKeyVersion(r.keyVersion());
    e.setIntegrityProfileRef(r.integrityProfileRef());
    e.setFirstSeenAt(r.firstSeenAt());
    e.setExpiresAt(r.expiresAt());
    e.setVersion(r.version());
    return e;
  }

  private static ReplayReservation toModel(SecurityReplayGuardEntity e) {
    return new ReplayReservation(
        e.getReservationId(),
        e.getReplayScopeHash(),
        e.getNonceHash(),
        e.getMessageFingerprint(),
        e.getFingerprintVersion(),
        e.getKeyRef(),
        e.getKeyVersion(),
        e.getIntegrityProfileRef(),
        e.getFirstSeenAt(),
        e.getExpiresAt(),
        ReplayDecisionStatus.valueOf(e.getStatus()),
        e.getVersion());
  }
}
