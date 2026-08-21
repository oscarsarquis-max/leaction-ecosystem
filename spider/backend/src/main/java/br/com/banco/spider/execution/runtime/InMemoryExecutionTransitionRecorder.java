package br.com.banco.spider.execution.runtime;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.support.SpiderClock;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

@Component
public class InMemoryExecutionTransitionRecorder implements ExecutionTransitionRecorderPort {

  private final SpiderClock clock;
  private final AtomicLong globalSequence = new AtomicLong(0);
  private final Map<String, List<ExecutionTransition>> byExecution = new ConcurrentHashMap<>();

  public InMemoryExecutionTransitionRecorder(SpiderClock clock) {
    this.clock = clock;
  }

  @Override
  public ExecutionTransition record(
      ExecutionRuntimeState state, ExecutionState toState, String reasonCode) {
    ExecutionState from = state.executionState();
    ExecutionStateMachine.assertAllowed(from, toState);
    ExecutionTransition transition =
        new ExecutionTransition(
            globalSequence.incrementAndGet(),
            state.executionId(),
            state.planId(),
            from,
            toState,
            clock.now(),
            reasonCode);
    state.apply(transition);
    byExecution
        .computeIfAbsent(state.executionId(), id -> new ArrayList<>())
        .add(transition);
    return transition;
  }

  @Override
  public List<ExecutionTransition> findByExecutionId(String executionId) {
    List<ExecutionTransition> list = byExecution.get(executionId);
    return list == null ? List.of() : List.copyOf(list);
  }

  @Override
  public void clear() {
    byExecution.clear();
    globalSequence.set(0);
  }
}
