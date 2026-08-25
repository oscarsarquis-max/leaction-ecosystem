package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionWaitStore implements ExecutionWaitStorePort {

  private final Map<String, ExecutionWaitRecord> byId = new ConcurrentHashMap<>();

  @Override
  public void insert(ExecutionWaitRecord wait) {
    if (byId.putIfAbsent(wait.waitId(), wait) != null) {
      throw new IllegalStateException("Wait already exists");
    }
  }

  @Override
  public Optional<ExecutionWaitRecord> findByWaitId(String waitId) {
    return Optional.ofNullable(byId.get(waitId));
  }

  @Override
  public Optional<ExecutionWaitRecord> findActiveByExecutionAndStep(
      String executionId, String stepId) {
    return byId.values().stream()
        .filter(
            w ->
                w.executionId().equals(executionId)
                    && w.stepId().equals(stepId)
                    && w.state().isActive())
        .findFirst();
  }

  @Override
  public Optional<ExecutionWaitRecord> findByExternalOperationRef(
      String sourceRef, String externalOperationRef) {
    return byId.values().stream()
        .filter(
            w ->
                sourceRef.equals(w.expectedSourceRef())
                    && externalOperationRef != null
                    && externalOperationRef.equals(w.externalOperationRef())
                    && w.state().isActive())
        .findFirst();
  }

  @Override
  public Optional<ExecutionWaitRecord> findByContinuationTokenFingerprint(String fingerprintDigest) {
    if (fingerprintDigest == null || fingerprintDigest.isBlank()) {
      return Optional.empty();
    }
    return byId.values().stream()
        .filter(
            w ->
                fingerprintDigest.equals(w.continuationTokenFingerprint())
                    && w.state().isActive())
        .findFirst();
  }

  @Override
  public List<ExecutionWaitRecord> findByExecutionId(String executionId) {
    if (executionId == null || executionId.isBlank()) {
      return List.of();
    }
    return byId.values().stream().filter(w -> executionId.equals(w.executionId())).toList();
  }

  @Override
  public synchronized ExecutionWaitRecord updateState(
      String waitId,
      WaitState expectedState,
      long expectedVersion,
      WaitState newState,
      String receivedMessageId,
      Instant resolvedAt,
      String resolutionReasonCode,
      Instant now) {
    ExecutionWaitRecord current = byId.get(waitId);
    if (current == null) {
      throw new IllegalStateException("Wait not found");
    }
    if (current.state() != expectedState || current.stateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException(
          "Wait state/version mismatch " + waitId);
    }
    ExecutionWaitRecord updated =
        current.withState(
            newState,
            current.stateVersion() + 1,
            receivedMessageId,
            resolvedAt,
            resolutionReasonCode);
    byId.put(waitId, updated);
    return updated;
  }

  @Override
  public List<ExecutionWaitRecord> findExpiredWaiting(Instant now) {
    return byId.values().stream()
        .filter(w -> w.state() == WaitState.WAITING && !w.expiresAt().isAfter(now))
        .toList();
  }

  @Override
  public List<ExecutionWaitRecord> findRecoverable() {
    return byId.values().stream()
        .filter(w -> w.state() == WaitState.RESUMING || w.state() == WaitState.SIGNALLED)
        .toList();
  }

  @Override
  public List<ExecutionWaitRecord> listActive(int maxResults) {
    return byId.values().stream()
        .filter(wait -> wait.state().isActive())
        .sorted(java.util.Comparator.comparing(ExecutionWaitRecord::createdAt))
        .limit(Math.max(0, maxResults))
        .toList();
  }

  public void clear() {
    byId.clear();
  }
}
