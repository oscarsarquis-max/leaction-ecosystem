package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionWaitEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionWaitJpaRepository;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
@ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
public class JpaExecutionWaitStoreAdapter implements ExecutionWaitStorePort {

  private final ExecutionWaitJpaRepository repo;

  public JpaExecutionWaitStoreAdapter(ExecutionWaitJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public void insert(ExecutionWaitRecord wait) {
    repo.save(toEntity(wait));
  }

  @Override
  public Optional<ExecutionWaitRecord> findByWaitId(String waitId) {
    return repo.findById(waitId).map(this::toModel);
  }

  @Override
  public Optional<ExecutionWaitRecord> findActiveByExecutionAndStep(
      String executionId, String stepId) {
    return repo.findActive(
            executionId,
            stepId,
            List.of(WaitState.WAITING, WaitState.SIGNALLED, WaitState.EXPIRING, WaitState.RESUMING))
        .map(this::toModel);
  }

  @Override
  public Optional<ExecutionWaitRecord> findByExternalOperationRef(
      String sourceRef, String externalOperationRef) {
    return repo.findByExpectedSourceRefAndExternalOperationRefAndStateIn(
            sourceRef,
            externalOperationRef,
            List.of(WaitState.WAITING, WaitState.SIGNALLED, WaitState.EXPIRING, WaitState.RESUMING))
        .map(this::toModel);
  }

  @Override
  public Optional<ExecutionWaitRecord> findByContinuationTokenFingerprint(String fingerprintDigest) {
    return repo.findByContinuationTokenFingerprint(fingerprintDigest).map(this::toModel);
  }

  @Override
  public List<ExecutionWaitRecord> findByExecutionId(String executionId) {
    return repo.findByExecutionId(executionId).stream().map(this::toModel).toList();
  }

  @Override
  @Transactional
  public ExecutionWaitRecord updateState(
      String waitId,
      WaitState expectedState,
      long expectedVersion,
      WaitState newState,
      String receivedMessageId,
      Instant resolvedAt,
      String resolutionReasonCode,
      Instant now) {
    ExecutionWaitEntity e =
        repo.findById(waitId).orElseThrow(() -> new IllegalStateException("Wait not found"));
    if (e.getState() != expectedState || e.getStateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException("Wait version mismatch");
    }
    e.setState(newState);
    e.setStateVersion(e.getStateVersion() + 1);
    if (receivedMessageId != null) {
      e.setReceivedMessageId(receivedMessageId);
    }
    if (resolvedAt != null) {
      e.setResolvedAt(resolvedAt);
    }
    if (resolutionReasonCode != null) {
      e.setResolutionReasonCode(resolutionReasonCode);
    }
    return toModel(repo.save(e));
  }

  @Override
  public List<ExecutionWaitRecord> findExpiredWaiting(Instant now) {
    return repo.findByStateAndExpiresAtLessThanEqual(WaitState.WAITING, now).stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  public List<ExecutionWaitRecord> findRecoverable() {
    return repo.findByStateIn(List.of(WaitState.RESUMING, WaitState.SIGNALLED)).stream()
        .map(this::toModel)
        .toList();
  }

  @Override
  public List<ExecutionWaitRecord> listActive(int maxResults) {
    return repo
        .findByStateIn(
            List.of(WaitState.WAITING, WaitState.SIGNALLED, WaitState.EXPIRING, WaitState.RESUMING))
        .stream()
        .sorted(java.util.Comparator.comparing(ExecutionWaitEntity::getCreatedAt))
        .limit(Math.max(0, maxResults))
        .map(this::toModel)
        .toList();
  }

  private ExecutionWaitEntity toEntity(ExecutionWaitRecord w) {
    ExecutionWaitEntity e = new ExecutionWaitEntity();
    e.setWaitId(w.waitId());
    e.setExecutionId(w.executionId());
    e.setStepId(w.stepId());
    e.setAttemptId(w.attemptId());
    e.setWaitType(w.waitType());
    e.setWaitPolicyRef(w.waitPolicyRef());
    e.setExternalOperationRef(w.externalOperationRef());
    e.setExpectedSignalContractRef(w.expectedSignalContractRef());
    e.setExpectedSourceRef(w.expectedSourceRef());
    e.setState(w.state());
    e.setStateVersion(w.stateVersion());
    e.setCreatedAt(w.createdAt());
    e.setEarliestResumeAt(w.earliestResumeAt());
    e.setExpiresAt(w.expiresAt());
    e.setReceivedMessageId(w.receivedMessageId());
    e.setResolvedAt(w.resolvedAt());
    e.setResolutionReasonCode(w.resolutionReasonCode());
    e.setSignalDefinitionRef(w.signalDefinitionRef());
    e.setIntegrityProfileRef(w.integrityProfileRef());
    e.setContinuationTokenFingerprint(w.continuationTokenFingerprint());
    e.setContinuationTokenFingerprintVersion(w.continuationTokenFingerprintVersion());
    e.setContinuationTokenKeyRef(w.continuationTokenKeyRef());
    e.setContinuationTokenKeyVersion(w.continuationTokenKeyVersion());
    e.setContinuationTokenExpiresAt(w.continuationTokenExpiresAt());
    e.setDataProtectionProfileRef(w.dataProtectionProfileRef());
    return e;
  }

  private ExecutionWaitRecord toModel(ExecutionWaitEntity e) {
    return new ExecutionWaitRecord(
        e.getWaitId(),
        e.getExecutionId(),
        e.getStepId(),
        e.getAttemptId(),
        e.getWaitType(),
        e.getWaitPolicyRef(),
        e.getExternalOperationRef(),
        e.getExpectedSignalContractRef(),
        e.getExpectedSourceRef(),
        e.getState(),
        e.getStateVersion(),
        e.getCreatedAt(),
        e.getEarliestResumeAt(),
        e.getExpiresAt(),
        e.getReceivedMessageId(),
        e.getResolvedAt(),
        e.getResolutionReasonCode(),
        e.getSignalDefinitionRef(),
        e.getIntegrityProfileRef(),
        e.getContinuationTokenFingerprint(),
        e.getContinuationTokenFingerprintVersion(),
        e.getContinuationTokenKeyRef(),
        e.getContinuationTokenKeyVersion(),
        e.getContinuationTokenExpiresAt(),
        e.getDataProtectionProfileRef());
  }
}
