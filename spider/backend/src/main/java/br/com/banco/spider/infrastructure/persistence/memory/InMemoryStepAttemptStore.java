package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;

public class InMemoryStepAttemptStore implements StepAttemptStorePort {

  private final Map<String, StepAttemptRecord> byId = new ConcurrentHashMap<>();
  private final Map<String, AtomicInteger> counters = new ConcurrentHashMap<>();

  private static String stepKey(String executionId, String stepId) {
    return executionId + "|" + stepId;
  }

  @Override
  public synchronized void insert(StepAttemptRecord attempt) {
    String sk = stepKey(attempt.executionId(), attempt.stepId());
    boolean dup =
        byId.values().stream()
            .anyMatch(
                a ->
                    a.executionId().equals(attempt.executionId())
                        && a.stepId().equals(attempt.stepId())
                        && a.attemptNumber() == attempt.attemptNumber());
    if (dup) {
      throw new IllegalStateException("Duplicate attempt number");
    }
    if (byId.putIfAbsent(attempt.attemptId(), attempt) != null) {
      throw new IllegalStateException("Attempt already exists");
    }
    counters
        .computeIfAbsent(sk, k -> new AtomicInteger(0))
        .updateAndGet(v -> Math.max(v, attempt.attemptNumber()));
  }

  @Override
  public void update(StepAttemptRecord attempt) {
    if (!byId.containsKey(attempt.attemptId())) {
      throw new IllegalStateException("Attempt not found");
    }
    byId.put(attempt.attemptId(), attempt);
  }

  @Override
  public Optional<StepAttemptRecord> findByAttemptId(String attemptId) {
    return Optional.ofNullable(byId.get(attemptId));
  }

  @Override
  public List<StepAttemptRecord> findByExecutionAndStep(String executionId, String stepId) {
    return byId.values().stream()
        .filter(a -> a.executionId().equals(executionId) && a.stepId().equals(stepId))
        .sorted(Comparator.comparingInt(StepAttemptRecord::attemptNumber))
        .toList();
  }

  @Override
  public int nextAttemptNumber(String executionId, String stepId) {
    return counters.computeIfAbsent(stepKey(executionId, stepId), k -> new AtomicInteger(0))
            .incrementAndGet();
  }

  public void clear() {
    byId.clear();
    counters.clear();
  }
}
