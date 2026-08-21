package br.com.banco.spider.execution.runtime;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ExecutionStateMachineTest {

  private InMemoryExecutionTransitionRecorder recorder;

  @BeforeEach
  void setUp() {
    recorder = new InMemoryExecutionTransitionRecorder(SpiderClock.fixed(Instant.parse("2026-01-01T00:00:00Z")));
    recorder.clear();
  }

  @Test
  void happyPathTransitionsAreMonotonic() {
    ExecutionRuntimeState state = new ExecutionRuntimeState("e1");
    recorder.record(state, ExecutionState.RECEIVED, "R");
    recorder.record(state, ExecutionState.VALIDATED, "V");
    recorder.record(state, ExecutionState.RESOLVED, "S");
    recorder.record(state, ExecutionState.PLANNED, "P");
    recorder.record(state, ExecutionState.RUNNING, "U");
    recorder.record(state, ExecutionState.SUCCEEDED, "OK");
    var transitions = recorder.findByExecutionId("e1");
    assertEquals(6, transitions.size());
    for (int i = 1; i < transitions.size(); i++) {
      assertTrue(transitions.get(i).sequence() > transitions.get(i - 1).sequence());
    }
  }

  @Test
  void invalidTransitionFails() {
    ExecutionRuntimeState state = new ExecutionRuntimeState("e1");
    recorder.record(state, ExecutionState.RECEIVED, "R");
    assertThrows(
        InvalidStateTransitionException.class,
        () -> recorder.record(state, ExecutionState.RUNNING, "bad"));
  }

  @Test
  void terminalDoesNotReopen() {
    ExecutionRuntimeState state = new ExecutionRuntimeState("e1");
    recorder.record(state, ExecutionState.RECEIVED, "R");
    recorder.record(state, ExecutionState.REJECTED, "X");
    assertThrows(
        InvalidStateTransitionException.class,
        () -> recorder.record(state, ExecutionState.VALIDATED, "reopen"));
  }

  @Test
  void runningToTimedOutAndWaitingAllowed() {
    ExecutionRuntimeState a = new ExecutionRuntimeState("a");
    pathToRunning(a);
    recorder.record(a, ExecutionState.TIMED_OUT, "T");

    ExecutionRuntimeState b = new ExecutionRuntimeState("b");
    pathToRunning(b);
    recorder.record(b, ExecutionState.WAITING_EXTERNAL, "W");
    assertEquals(ExecutionState.WAITING_EXTERNAL, b.executionState());
  }

  @Test
  void waitingExternalCanResumeToRunning() {
    ExecutionRuntimeState b = new ExecutionRuntimeState("b");
    pathToRunning(b);
    recorder.record(b, ExecutionState.WAITING_EXTERNAL, "W");
    recorder.record(b, ExecutionState.RUNNING, "RESUME");
    assertEquals(ExecutionState.RUNNING, b.executionState());
  }

  private void pathToRunning(ExecutionRuntimeState state) {
    recorder.record(state, ExecutionState.RECEIVED, "R");
    recorder.record(state, ExecutionState.VALIDATED, "V");
    recorder.record(state, ExecutionState.RESOLVED, "S");
    recorder.record(state, ExecutionState.PLANNED, "P");
    recorder.record(state, ExecutionState.RUNNING, "U");
  }
}
