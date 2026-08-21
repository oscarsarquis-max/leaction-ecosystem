package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionControlStore implements ExecutionControlStorePort {

  private final Map<String, ExecutionControlRecord> byId = new ConcurrentHashMap<>();

  @Override
  public void insert(ExecutionControlRecord record) {
    if (byId.putIfAbsent(record.executionId(), record) != null) {
      throw new IllegalStateException("Execution already exists: " + record.executionId());
    }
  }

  @Override
  public Optional<ExecutionControlRecord> findByExecutionId(String executionId) {
    return Optional.ofNullable(byId.get(executionId));
  }

  @Override
  public ExecutionControlRecord updateState(
      String executionId,
      ExecutionState expectedState,
      long expectedVersion,
      ExecutionState newState,
      TechnicalStatus technicalStatus,
      String planId,
      String routeCode,
      String routeVersion,
      String activeWaitType,
      Instant startedAt,
      Instant completedAt,
      Instant lastUpdatedAt) {
    ExecutionControlRecord current = byId.get(executionId);
    if (current == null) {
      throw new IllegalStateException("Execution not found: " + executionId);
    }
    if (current.state() != expectedState || current.stateVersion() != expectedVersion) {
      throw new OptimisticLockException(
          "State/version mismatch for " + executionId + " expected=" + expectedState + "@" + expectedVersion
              + " actual=" + current.state() + "@" + current.stateVersion());
    }
    ExecutionControlRecord updated =
        new ExecutionControlRecord(
            current.executionId(),
            current.contextId(),
            current.correlationId(),
            planId != null ? planId : current.planId(),
            routeCode != null ? routeCode : current.routeCode(),
            routeVersion != null ? routeVersion : current.routeVersion(),
            newState,
            current.stateVersion() + 1,
            technicalStatus != null ? technicalStatus : current.technicalStatus(),
            startedAt != null ? startedAt : current.startedAt(),
            completedAt != null ? completedAt : current.completedAt(),
            lastUpdatedAt,
            activeWaitType != null ? activeWaitType : current.activeWaitType(),
            current.retentionClassRef(),
            current.ownerPrincipalRef());
    byId.put(executionId, updated);
    return updated;
  }

  @Override
  public List<ExecutionControlRecord> findByStates(List<ExecutionState> states) {
    return byId.values().stream().filter(r -> states.contains(r.state())).toList();
  }

  @Override
  public List<ExecutionControlRecord> listRecent(
      int limit, Instant cursorStartedAt, String cursorExecutionId) {
    return byId.values().stream()
        .sorted(
            (a, b) -> {
              Instant as = a.startedAt() == null ? Instant.EPOCH : a.startedAt();
              Instant bs = b.startedAt() == null ? Instant.EPOCH : b.startedAt();
              int c = bs.compareTo(as);
              if (c != 0) {
                return c;
              }
              return b.executionId().compareTo(a.executionId());
            })
        .filter(
            r -> {
              if (cursorStartedAt == null || cursorExecutionId == null) {
                return true;
              }
              Instant s = r.startedAt() == null ? Instant.EPOCH : r.startedAt();
              int cmp = s.compareTo(cursorStartedAt);
              if (cmp < 0) {
                return true;
              }
              if (cmp > 0) {
                return false;
              }
              return r.executionId().compareTo(cursorExecutionId) < 0;
            })
        .limit(Math.max(1, limit))
        .toList();
  }

  public void clear() {
    byId.clear();
  }

  public static final class OptimisticLockException extends RuntimeException {
    public OptimisticLockException(String message) {
      super(message);
    }
  }
}
