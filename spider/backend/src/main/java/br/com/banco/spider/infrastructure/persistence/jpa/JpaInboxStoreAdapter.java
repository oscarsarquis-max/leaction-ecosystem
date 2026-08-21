package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.inbox.InboxProcessingState;
import br.com.banco.spider.execution.inbox.InboxRecord;
import br.com.banco.spider.execution.inbox.InboxReservationResult;
import br.com.banco.spider.execution.inbox.InboxValidationState;
import br.com.banco.spider.execution.persistence.port.InboxStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.InboxMessageEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.InboxMessageJpaRepository;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaInboxStoreAdapter implements InboxStorePort {

  private final InboxMessageJpaRepository repo;

  public JpaInboxStoreAdapter(InboxMessageJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public InboxReservationResult reserve(InboxRecord candidate) {
    InboxMessageEntity.Pk pk =
        new InboxMessageEntity.Pk(candidate.sourceRef(), candidate.messageId());
    Optional<InboxMessageEntity> existing = repo.findById(pk);
    if (existing.isPresent()) {
      return compareExisting(existing.get(), candidate);
    }
    try {
      repo.save(toEntity(candidate));
      return InboxReservationResult.reserved(candidate);
    } catch (DataIntegrityViolationException ex) {
      InboxMessageEntity raced =
          repo.findById(pk).orElseThrow(() -> new IllegalStateException("Inbox race", ex));
      return compareExisting(raced, candidate);
    }
  }

  private InboxReservationResult compareExisting(InboxMessageEntity existing, InboxRecord candidate) {
    if (existing.getMessageFingerprint().equals(candidate.messageFingerprint())) {
      if (existing.getProcessingState() == InboxProcessingState.PROCESSING
          || existing.getProcessingState() == InboxProcessingState.APPLYING) {
        return InboxReservationResult.inProgress(toModel(existing));
      }
      return InboxReservationResult.duplicate(toModel(existing));
    }
    existing.setProcessingState(InboxProcessingState.CONFLICT);
    existing.setErrorCode("FINGERPRINT_CONFLICT");
    repo.save(existing);
    return InboxReservationResult.conflict(toModel(existing));
  }

  @Override
  public Optional<InboxRecord> find(String sourceRef, String messageId) {
    return repo.findById(new InboxMessageEntity.Pk(sourceRef, messageId)).map(this::toModel);
  }

  @Override
  @Transactional
  public InboxRecord updateStates(
      String sourceRef,
      String messageId,
      InboxValidationState validationState,
      InboxProcessingState processingState,
      String payloadRef,
      String errorCode) {
    InboxMessageEntity e =
        repo.findById(new InboxMessageEntity.Pk(sourceRef, messageId))
            .orElseThrow(() -> new IllegalStateException("Inbox not found"));
    if (validationState != null) {
      e.setValidationState(validationState);
    }
    if (processingState != null) {
      e.setProcessingState(processingState);
    }
    if (payloadRef != null) {
      e.setPayloadRef(payloadRef);
    }
    if (errorCode != null) {
      e.setErrorCode(errorCode);
    }
    return toModel(repo.save(e));
  }

  @Override
  public List<InboxRecord> findByProcessingState(InboxProcessingState state) {
    return repo.findByProcessingState(state).stream().map(this::toModel).toList();
  }

  @Override
  public List<InboxRecord> findInterruptedProcessing() {
    return findByProcessingState(InboxProcessingState.PROCESSING);
  }

  @Override
  public List<InboxRecord> findDueForApplication(Instant now, int limit) {
    return repo.findByProcessingState(InboxProcessingState.APPLY_PENDING).stream()
        .map(this::toModel)
        .filter(
            r ->
                (r.nextAttemptAt() == null || !r.nextAttemptAt().isAfter(now))
                    && (r.leaseUntil() == null || !r.leaseUntil().isAfter(now)))
        .sorted(
            Comparator.comparing(
                    (InboxRecord r) -> r.nextAttemptAt() == null ? Instant.EPOCH : r.nextAttemptAt())
                .thenComparing(InboxRecord::messageId))
        .limit(Math.max(1, limit))
        .toList();
  }

  @Override
  @Transactional
  public Optional<InboxRecord> claimForApplication(
      String sourceRef,
      String messageId,
      long expectedVersion,
      String workerId,
      Instant leaseUntil,
      Instant now) {
    InboxMessageEntity e =
        repo.findById(new InboxMessageEntity.Pk(sourceRef, messageId)).orElse(null);
    if (e == null
        || safeVersion(e) != expectedVersion
        || e.getProcessingState() != InboxProcessingState.APPLY_PENDING) {
      return Optional.empty();
    }
    if (e.getLeaseUntil() != null && e.getLeaseUntil().isAfter(now)) {
      return Optional.empty();
    }
    e.setProcessingState(InboxProcessingState.APPLYING);
    e.setLeaseOwner(workerId);
    e.setLeaseUntil(leaseUntil);
    e.setApplicationAttemptCount(safeAttempts(e) + 1);
    e.setOptimisticVersion(safeVersion(e) + 1);
    return Optional.of(toModel(repo.save(e)));
  }

  @Override
  @Transactional
  public InboxRecord updateApplicationState(
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
    InboxMessageEntity e =
        repo.findById(new InboxMessageEntity.Pk(sourceRef, messageId))
            .orElseThrow(() -> new IllegalStateException("Inbox not found"));
    if (safeVersion(e) != expectedVersion) {
      throw new IllegalStateException("Inbox optimistic lock failed");
    }
    e.setProcessingState(processingState);
    e.setLeaseOwner(leaseOwner);
    e.setLeaseUntil(leaseUntil);
    e.setNextAttemptAt(nextAttemptAt);
    e.setApplicationAttemptCount(applicationAttemptCount);
    if (errorCode != null) {
      e.setErrorCode(errorCode);
    }
    if (appliedAt != null) {
      e.setAppliedAt(appliedAt);
    }
    if (e.getVerifiedAt() == null) {
      e.setVerifiedAt(now);
    }
    e.setOptimisticVersion(safeVersion(e) + 1);
    return toModel(repo.save(e));
  }

  private static long safeVersion(InboxMessageEntity e) {
    return e.getOptimisticVersion() == null ? 0L : e.getOptimisticVersion();
  }

  private static int safeAttempts(InboxMessageEntity e) {
    return e.getApplicationAttemptCount() == null ? 0 : e.getApplicationAttemptCount();
  }

  private InboxMessageEntity toEntity(InboxRecord r) {
    InboxMessageEntity e = new InboxMessageEntity();
    e.setSourceRef(r.sourceRef());
    e.setMessageId(r.messageId());
    e.setBindingRef(r.bindingRef());
    e.setContractRef(r.contractRef());
    e.setDeduplicationKeyHash(r.deduplicationKeyHash());
    e.setMessageFingerprint(r.messageFingerprint());
    e.setFingerprintVersion(r.fingerprintVersion());
    e.setExecutionId(r.executionId());
    e.setStepId(r.stepId());
    e.setExternalOperationRef(r.externalOperationRef());
    e.setReceivedAt(r.receivedAt());
    e.setValidationState(r.validationState());
    e.setProcessingState(r.processingState());
    e.setPayloadRef(r.payloadRef());
    e.setErrorCode(r.errorCode());
    e.setExpiresAt(r.expiresAt());
    e.setWaitId(r.waitId());
    e.setSignalDefinitionRef(r.signalDefinitionRef());
    e.setPayloadDigest(r.payloadDigest());
    e.setApplicationAttemptCount(r.applicationAttemptCount());
    e.setNextAttemptAt(r.nextAttemptAt());
    e.setLeaseOwner(r.leaseOwner());
    e.setLeaseUntil(r.leaseUntil());
    e.setOptimisticVersion(r.version());
    e.setVerifiedAt(r.verifiedAt());
    e.setAppliedAt(r.appliedAt());
    return e;
  }

  private InboxRecord toModel(InboxMessageEntity e) {
    return new InboxRecord(
        e.getMessageId(),
        e.getSourceRef(),
        e.getBindingRef(),
        e.getContractRef(),
        e.getDeduplicationKeyHash(),
        e.getMessageFingerprint(),
        e.getFingerprintVersion(),
        e.getExecutionId(),
        e.getStepId(),
        e.getExternalOperationRef(),
        e.getReceivedAt(),
        e.getValidationState(),
        e.getProcessingState(),
        e.getPayloadRef(),
        e.getErrorCode(),
        e.getExpiresAt(),
        e.getWaitId(),
        e.getSignalDefinitionRef(),
        e.getPayloadDigest(),
        safeAttempts(e),
        e.getNextAttemptAt(),
        e.getLeaseOwner(),
        e.getLeaseUntil(),
        safeVersion(e),
        e.getVerifiedAt(),
        e.getAppliedAt());
  }
}
