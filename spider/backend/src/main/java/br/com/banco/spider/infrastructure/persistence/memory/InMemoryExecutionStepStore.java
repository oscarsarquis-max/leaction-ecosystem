package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepState;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionStepStore implements ExecutionStepStorePort {

  private final Map<String, ExecutionStepRecord> byKey = new ConcurrentHashMap<>();

  private static String key(String executionId, String stepId) {
    return executionId + "|" + stepId;
  }

  @Override
  public void insertAll(List<ExecutionStepRecord> steps) {
    for (ExecutionStepRecord s : steps) {
      if (byKey.putIfAbsent(key(s.executionId(), s.stepId()), s) != null) {
        throw new IllegalStateException("Step already exists: " + s.stepId());
      }
    }
  }

  @Override
  public Optional<ExecutionStepRecord> find(String executionId, String stepId) {
    return Optional.ofNullable(byKey.get(key(executionId, stepId)));
  }

  @Override
  public List<ExecutionStepRecord> findByExecutionIdOrdered(String executionId) {
    return byKey.values().stream()
        .filter(s -> s.executionId().equals(executionId))
        .sorted(Comparator.comparingInt(ExecutionStepRecord::orderedPosition))
        .toList();
  }

  @Override
  public ExecutionStepRecord updateState(
      String executionId,
      String stepId,
      StepState expectedState,
      long expectedVersion,
      StepState newState,
      String activeAttemptId,
      String outputResultRef,
      String terminalErrorCode,
      Instant startedAt,
      Instant completedAt,
      Instant lastUpdatedAt) {
    ExecutionStepRecord current = byKey.get(key(executionId, stepId));
    if (current == null) {
      throw new IllegalStateException("Step not found");
    }
    if (current.state() != expectedState || current.stateVersion() != expectedVersion) {
      throw new InMemoryExecutionControlStore.OptimisticLockException(
          "Step state/version mismatch " + stepId);
    }
    ExecutionStepRecord updated =
        new ExecutionStepRecord(
            current.executionId(),
            current.stepId(),
            current.orderedPosition(),
            newState,
            current.stateVersion() + 1,
            activeAttemptId,
            outputResultRef != null ? outputResultRef : current.outputResultRef(),
            terminalErrorCode != null ? terminalErrorCode : current.terminalErrorCode(),
            startedAt != null ? startedAt : current.startedAt(),
            completedAt != null ? completedAt : current.completedAt(),
            lastUpdatedAt);
    byKey.put(key(executionId, stepId), updated);
    return updated;
  }

  @Override
  public List<ExecutionStepRecord> findByStates(List<StepState> states) {
    return byKey.values().stream().filter(s -> states.contains(s.state())).toList();
  }

  public void clear() {
    byKey.clear();
  }
}
