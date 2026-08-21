package br.com.banco.spider.execution.runtime;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.domain.ExecutionState;
import java.time.Instant;
import java.util.EnumMap;
import java.util.EnumSet;
import java.util.Map;
import java.util.Set;
import java.util.UUID;

/** Máquina de estados mínima da vertical slice (SPIDER-ARCH-005). */
public final class ExecutionStateMachine {

  private static final Map<ExecutionState, Set<ExecutionState>> ALLOWED = new EnumMap<>(ExecutionState.class);

  static {
    ALLOWED.put(ExecutionState.RECEIVED, EnumSet.of(ExecutionState.VALIDATED, ExecutionState.REJECTED));
    ALLOWED.put(ExecutionState.VALIDATED, EnumSet.of(ExecutionState.RESOLVED, ExecutionState.REJECTED));
    ALLOWED.put(ExecutionState.RESOLVED, EnumSet.of(ExecutionState.PLANNED, ExecutionState.REJECTED));
    ALLOWED.put(ExecutionState.PLANNED, EnumSet.of(ExecutionState.RUNNING, ExecutionState.REJECTED));
    ALLOWED.put(
        ExecutionState.RUNNING,
        EnumSet.of(
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED,
            ExecutionState.TIMED_OUT,
            ExecutionState.WAITING_EXTERNAL));
    ALLOWED.put(
        ExecutionState.WAITING_EXTERNAL,
        EnumSet.of(
            ExecutionState.RUNNING,
            ExecutionState.SUCCEEDED,
            ExecutionState.FAILED,
            ExecutionState.TIMED_OUT,
            ExecutionState.WAITING_EXTERNAL));
  }

  private ExecutionStateMachine() {}

  public static void assertAllowed(ExecutionState from, ExecutionState to) {
    if (to == null) {
      throw new InvalidStateTransitionException(from, null, "Target state is required");
    }
    if (from == null) {
      if (to != ExecutionState.RECEIVED) {
        throw new InvalidStateTransitionException(from, to, "Bootstrap must enter RECEIVED");
      }
      return;
    }
    if (from.isTerminal()) {
      throw new InvalidStateTransitionException(from, to, "Terminal state cannot reopen");
    }
    Set<ExecutionState> next = ALLOWED.getOrDefault(from, EnumSet.noneOf(ExecutionState.class));
    if (!next.contains(to)) {
      throw new InvalidStateTransitionException(from, to, "Transition not allowed in this increment");
    }
  }

  public static CanonicalError toCanonicalError(InvalidStateTransitionException ex) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code("INT_INVALID_STATE_TRANSITION")
        .category(ErrorCategory.INTERNAL)
        .severity(ErrorSeverity.FATAL)
        .message(ex.getMessage())
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("state_machine", null, null, null))
        .build();
  }
}
