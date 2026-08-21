package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelope;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ProtectedSignalEnvelopeEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ProtectedSignalEnvelopeJpaRepository;
import br.com.banco.spider.security.dataprotection.ProtectedPayloadService;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaProtectedSignalEnvelopeStoreAdapter implements ProtectedSignalEnvelopeStorePort {

  private final ProtectedSignalEnvelopeJpaRepository repo;

  public JpaProtectedSignalEnvelopeStoreAdapter(ProtectedSignalEnvelopeJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public ProtectedSignalEnvelope createOnce(ProtectedSignalEnvelope envelope) {
    Optional<ProtectedSignalEnvelopeEntity> existing =
        repo.findByInboxLogicalKey(envelope.inboxLogicalKey());
    if (existing.isPresent()) {
      return toModel(existing.get());
    }
    return toModel(repo.save(toEntity(envelope)));
  }

  @Override
  public Optional<ProtectedSignalEnvelope> findByInboxLogicalKey(String inboxLogicalKey) {
    return repo.findByInboxLogicalKey(inboxLogicalKey).map(this::toModel);
  }

  @Override
  @Transactional
  public Optional<ProtectedSignalEnvelope> claim(
      String inboxLogicalKey,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now) {
    ProtectedSignalEnvelopeEntity e =
        repo.findByInboxLogicalKey(inboxLogicalKey).orElse(null);
    if (e == null
        || e.getOptimisticVersion() != expectedVersion
        || e.getState() != ProtectedEnvelopeState.AVAILABLE) {
      return Optional.empty();
    }
    if (e.getLeaseUntil() != null && e.getLeaseUntil().isAfter(now)) {
      return Optional.empty();
    }
    e.setState(ProtectedEnvelopeState.CLAIMED);
    e.setLeaseOwner(workerId);
    e.setLeaseUntil(leaseUntil);
    e.setOptimisticVersion(e.getOptimisticVersion() + 1);
    return Optional.of(toModel(repo.save(e)));
  }

  @Override
  @Transactional
  public ProtectedSignalEnvelope updateState(
      String inboxLogicalKey,
      long expectedVersion,
      ProtectedEnvelopeState state,
      String leaseOwner,
      Instant leaseUntil,
      Instant consumedAt,
      Instant eligibleForDeletionAt) {
    ProtectedSignalEnvelopeEntity e =
        repo.findByInboxLogicalKey(inboxLogicalKey)
            .orElseThrow(() -> new IllegalStateException("Protected envelope not found"));
    if (e.getOptimisticVersion() != expectedVersion) {
      throw new IllegalStateException("Protected envelope optimistic lock failed");
    }
    e.setState(state);
    e.setLeaseOwner(leaseOwner);
    e.setLeaseUntil(leaseUntil);
    if (consumedAt != null) {
      e.setConsumedAt(consumedAt);
    }
    if (eligibleForDeletionAt != null) {
      e.setEligibleForDeletionAt(eligibleForDeletionAt);
    }
    e.setOptimisticVersion(e.getOptimisticVersion() + 1);
    return toModel(repo.save(e));
  }

  @Override
  public List<ProtectedSignalEnvelope> findByState(ProtectedEnvelopeState state) {
    return repo.findByState(state).stream().map(this::toModel).toList();
  }

  private ProtectedSignalEnvelopeEntity toEntity(ProtectedSignalEnvelope m) {
    ProtectedSignalEnvelopeEntity e = new ProtectedSignalEnvelopeEntity();
    e.setProtectedEnvelopeId(m.protectedEnvelopeId());
    e.setInboxLogicalKey(m.inboxLogicalKey());
    e.setDataProtectionProfileRef(m.dataProtectionProfileRef());
    e.setAlgorithm(m.algorithm());
    e.setKeyRef(m.keyRef());
    e.setKeyVersion(m.keyVersion());
    e.setAadVersion(m.aadVersion());
    e.setIvB64(ProtectedPayloadService.encodeB64(m.iv()));
    e.setCiphertextAndTagB64(ProtectedPayloadService.encodeB64(m.ciphertextAndTag()));
    e.setPlaintextDigest(m.plaintextDigest());
    e.setCiphertextDigest(m.ciphertextDigest());
    e.setPlaintextSize(m.plaintextSize());
    e.setState(m.state());
    e.setCreatedAt(m.createdAt());
    e.setConsumedAt(m.consumedAt());
    e.setEligibleForDeletionAt(m.eligibleForDeletionAt());
    e.setLeaseOwner(m.leaseOwner());
    e.setLeaseUntil(m.leaseUntil());
    e.setOptimisticVersion(m.optimisticVersion());
    return e;
  }

  private ProtectedSignalEnvelope toModel(ProtectedSignalEnvelopeEntity e) {
    return new ProtectedSignalEnvelope(
        e.getProtectedEnvelopeId(),
        e.getInboxLogicalKey(),
        e.getDataProtectionProfileRef(),
        e.getAlgorithm(),
        e.getKeyRef(),
        e.getKeyVersion(),
        e.getAadVersion(),
        ProtectedPayloadService.decodeB64(e.getIvB64()),
        ProtectedPayloadService.decodeB64(e.getCiphertextAndTagB64()),
        e.getPlaintextDigest(),
        e.getCiphertextDigest(),
        e.getPlaintextSize(),
        e.getState(),
        e.getCreatedAt(),
        e.getConsumedAt(),
        e.getEligibleForDeletionAt(),
        e.getLeaseOwner(),
        e.getLeaseUntil(),
        e.getOptimisticVersion());
  }
}
