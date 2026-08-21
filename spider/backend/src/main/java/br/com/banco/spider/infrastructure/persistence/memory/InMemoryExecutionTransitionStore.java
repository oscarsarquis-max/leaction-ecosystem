package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

public class InMemoryExecutionTransitionStore implements ExecutionTransitionStorePort {

  private final Map<String, List<ExecutionTransitionRecord>> byExecution = new ConcurrentHashMap<>();
  private final Map<String, AtomicLong> sequences = new ConcurrentHashMap<>();

  @Override
  public synchronized void append(ExecutionTransitionRecord transition) {
    List<ExecutionTransitionRecord> list =
        byExecution.computeIfAbsent(transition.executionId(), id -> new ArrayList<>());
    boolean dup =
        list.stream().anyMatch(t -> t.sequence() == transition.sequence());
    if (dup) {
      throw new IllegalStateException(
          "Duplicate transition sequence " + transition.sequence() + " for " + transition.executionId());
    }
    list.add(transition);
    sequences
        .computeIfAbsent(transition.executionId(), id -> new AtomicLong(0))
        .updateAndGet(v -> Math.max(v, transition.sequence()));
  }

  @Override
  public List<ExecutionTransitionRecord> findByExecutionId(String executionId) {
    List<ExecutionTransitionRecord> list = byExecution.get(executionId);
    return list == null ? List.of() : List.copyOf(list);
  }

  @Override
  public long nextSequence(String executionId) {
    return sequences.computeIfAbsent(executionId, id -> new AtomicLong(0)).incrementAndGet();
  }

  public void clear() {
    byExecution.clear();
    sequences.clear();
  }
}
