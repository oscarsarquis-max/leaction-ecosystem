package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelope;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelopeStorePort;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

@Component
@ConditionalOnProperty(
    name = "spider.canonical.persistence.mode",
    havingValue = "memory",
    matchIfMissing = true)
public class InMemoryProtectedSignalEnvelopeStore implements ProtectedSignalEnvelopeStorePort {

  private final Map<String, ProtectedSignalEnvelope> byInbox = new ConcurrentHashMap<>();

  @Override
  public synchronized ProtectedSignalEnvelope createOnce(ProtectedSignalEnvelope envelope) {
    if (byInbox.containsKey(envelope.inboxLogicalKey())) {
      return byInbox.get(envelope.inboxLogicalKey());
    }
    byInbox.put(envelope.inboxLogicalKey(), envelope);
    return envelope;
  }

  @Override
  public Optional<ProtectedSignalEnvelope> findByInboxLogicalKey(String inboxLogicalKey) {
    return Optional.ofNullable(byInbox.get(inboxLogicalKey));
  }

  @Override
  public synchronized Optional<ProtectedSignalEnvelope> claim(
      String inboxLogicalKey,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now) {
    ProtectedSignalEnvelope current = byInbox.get(inboxLogicalKey);
    if (current == null
        || current.optimisticVersion() != expectedVersion
        || current.state() != ProtectedEnvelopeState.AVAILABLE) {
      return Optional.empty();
    }
    if (current.leaseUntil() != null && current.leaseUntil().isAfter(now)) {
      return Optional.empty();
    }
    ProtectedSignalEnvelope claimed =
        new ProtectedSignalEnvelope(
            current.protectedEnvelopeId(),
            current.inboxLogicalKey(),
            current.dataProtectionProfileRef(),
            current.algorithm(),
            current.keyRef(),
            current.keyVersion(),
            current.aadVersion(),
            current.iv(),
            current.ciphertextAndTag(),
            current.plaintextDigest(),
            current.ciphertextDigest(),
            current.plaintextSize(),
            ProtectedEnvelopeState.CLAIMED,
            current.createdAt(),
            current.consumedAt(),
            current.eligibleForDeletionAt(),
            workerId,
            leaseUntil,
            current.optimisticVersion() + 1);
    byInbox.put(inboxLogicalKey, claimed);
    return Optional.of(claimed);
  }

  @Override
  public synchronized ProtectedSignalEnvelope updateState(
      String inboxLogicalKey,
      long expectedVersion,
      ProtectedEnvelopeState state,
      String leaseOwner,
      Instant leaseUntil,
      Instant consumedAt,
      Instant eligibleForDeletionAt) {
    ProtectedSignalEnvelope current = byInbox.get(inboxLogicalKey);
    if (current == null || current.optimisticVersion() != expectedVersion) {
      throw new IllegalStateException("Protected envelope optimistic lock failed");
    }
    ProtectedSignalEnvelope updated =
        new ProtectedSignalEnvelope(
            current.protectedEnvelopeId(),
            current.inboxLogicalKey(),
            current.dataProtectionProfileRef(),
            current.algorithm(),
            current.keyRef(),
            current.keyVersion(),
            current.aadVersion(),
            current.iv(),
            current.ciphertextAndTag(),
            current.plaintextDigest(),
            current.ciphertextDigest(),
            current.plaintextSize(),
            state,
            current.createdAt(),
            consumedAt != null ? consumedAt : current.consumedAt(),
            eligibleForDeletionAt != null ? eligibleForDeletionAt : current.eligibleForDeletionAt(),
            leaseOwner,
            leaseUntil,
            current.optimisticVersion() + 1);
    byInbox.put(inboxLogicalKey, updated);
    return updated;
  }

  @Override
  public List<ProtectedSignalEnvelope> findByState(ProtectedEnvelopeState state) {
    return byInbox.values().stream().filter(e -> e.state() == state).toList();
  }
}
