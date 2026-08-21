package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationResult;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryInboxStore implements InboxStorePort {

  private final Map<String, InboxRecord> byKey = new ConcurrentHashMap<>();

  private static String key(String sourceRef, String messageId) {
    return sourceRef + "|" + messageId;
  }

  @Override
  public synchronized InboxReservationResult reserve(InboxRecord candidate) {
    String k = key(candidate.sourceRef(), candidate.messageId());
    InboxRecord existing = byKey.get(k);
    if (existing == null) {
      byKey.put(k, candidate);
      return InboxReservationResult.reserved(candidate);
    }
    if (existing.messageFingerprint().equals(candidate.messageFingerprint())) {
      if (existing.processingState() == InboxProcessingState.PROCESSING
          || existing.processingState() == InboxProcessingState.APPLYING) {
        return InboxReservationResult.inProgress(existing);
      }
      return InboxReservationResult.duplicate(existing);
    }
    InboxRecord conflict =
        updateStates(
            existing.sourceRef(),
            existing.messageId(),
            existing.validationState(),
            InboxProcessingState.CONFLICT,
            existing.payloadRef(),
            "FINGERPRINT_CONFLICT");
    return InboxReservationResult.conflict(conflict);
  }

  @Override
  public Optional<InboxRecord> find(String sourceRef, String messageId) {
    return Optional.ofNullable(byKey.get(key(sourceRef, messageId)));
  }

  @Override
  public synchronized InboxRecord updateStates(
      String sourceRef,
      String messageId,
      InboxValidationState validationState,
      InboxProcessingState processingState,
      String payloadRef,
      String errorCode) {
    InboxRecord current = byKey.get(key(sourceRef, messageId));
    if (current == null) {
      throw new IllegalStateException("Inbox message not found");
    }
    InboxRecord updated =
        current.withProcessing(validationState, processingState, payloadRef, errorCode);
    byKey.put(key(sourceRef, messageId), updated);
    return updated;
  }

  @Override
  public List<InboxRecord> findByProcessingState(InboxProcessingState state) {
    return byKey.values().stream().filter(r -> r.processingState() == state).toList();
  }

  @Override
  public List<InboxRecord> findInterruptedProcessing() {
    return byKey.values().stream()
        .filter(
            r ->
                r.processingState() == InboxProcessingState.PROCESSING
                    || r.processingState() == InboxProcessingState.APPLYING)
        .toList();
  }

  @Override
  public synchronized List<InboxRecord> findDueForApplication(Instant now, int limit) {
    return byKey.values().stream()
        .filter(
            r ->
                r.processingState() == InboxProcessingState.APPLY_PENDING
                    && (r.nextAttemptAt() == null || !r.nextAttemptAt().isAfter(now))
                    && (r.leaseUntil() == null || !r.leaseUntil().isAfter(now)))
        .sorted(
            Comparator.comparing(
                    (InboxRecord r) -> r.nextAttemptAt() == null ? Instant.EPOCH : r.nextAttemptAt())
                .thenComparing(InboxRecord::messageId))
        .limit(Math.max(1, limit))
        .toList();
  }

  @Override
  public synchronized Optional<InboxRecord> claimForApplication(
      String sourceRef,
      String messageId,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now) {
    InboxRecord current = byKey.get(key(sourceRef, messageId));
    if (current == null
        || current.version() != expectedVersion
        || current.processingState() != InboxProcessingState.APPLY_PENDING) {
      return Optional.empty();
    }
    if (current.leaseUntil() != null && current.leaseUntil().isAfter(now)) {
      return Optional.empty();
    }
    InboxRecord claimed =
        new InboxRecord(
            current.messageId(),
            current.sourceRef(),
            current.bindingRef(),
            current.contractRef(),
            current.deduplicationKeyHash(),
            current.messageFingerprint(),
            current.fingerprintVersion(),
            current.executionId(),
            current.stepId(),
            current.externalOperationRef(),
            current.receivedAt(),
            current.validationState(),
            InboxProcessingState.APPLYING,
            current.payloadRef(),
            current.errorCode(),
            current.expiresAt(),
            current.waitId(),
            current.signalDefinitionRef(),
            current.payloadDigest(),
            current.applicationAttemptCount() + 1,
            current.nextAttemptAt(),
            workerId,
            leaseUntil,
            current.version() + 1,
            current.verifiedAt(),
            current.appliedAt());
    byKey.put(key(sourceRef, messageId), claimed);
    return Optional.of(claimed);
  }

  @Override
  public synchronized InboxRecord updateApplicationState(
      String sourceRef,
      String messageId,
      long expectedVersion,
      InboxProcessingState processingState,
      String leaseOwner,
      Instant leaseUntil,
      Instant nextAttemptAt,
      int applicationAttemptCount,
      String errorCode,
      Instant appliedAt,
      Instant now) {
    InboxRecord current = byKey.get(key(sourceRef, messageId));
    if (current == null || current.version() != expectedVersion) {
      throw new IllegalStateException("Inbox optimistic lock failed");
    }
    InboxRecord updated =
        new InboxRecord(
            current.messageId(),
            current.sourceRef(),
            current.bindingRef(),
            current.contractRef(),
            current.deduplicationKeyHash(),
            current.messageFingerprint(),
            current.fingerprintVersion(),
            current.executionId(),
            current.stepId(),
            current.externalOperationRef(),
            current.receivedAt(),
            current.validationState(),
            processingState,
            current.payloadRef(),
            errorCode != null ? errorCode : current.errorCode(),
            current.expiresAt(),
            current.waitId(),
            current.signalDefinitionRef(),
            current.payloadDigest(),
            applicationAttemptCount,
            nextAttemptAt,
            leaseOwner,
            leaseUntil,
            current.version() + 1,
            current.verifiedAt() != null ? current.verifiedAt() : now,
            appliedAt != null ? appliedAt : current.appliedAt());
    byKey.put(key(sourceRef, messageId), updated);
    return updated;
  }

  public void clear() {
    byKey.clear();
  }
}
