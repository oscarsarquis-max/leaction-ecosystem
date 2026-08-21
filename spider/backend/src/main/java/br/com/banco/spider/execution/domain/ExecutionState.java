package br.com.banco.spider.execution.domain;

import java.util.EnumSet;
import java.util.Set;

/** Máquina de estados técnica da execução (SPIDER-ARCH-003/005). Serialização por nome. */
public enum ExecutionState {
  RECEIVED,
  VALIDATED,
  RESOLVED,
  PLANNED,
  RUNNING,
  WAITING_EXTERNAL,
  COMPENSATING,
  SUCCEEDED,
  PARTIALLY_SUCCEEDED,
  COMPENSATED,
  FAILED,
  TIMED_OUT,
  REJECTED,
  CANCELLED;

  private static final Set<ExecutionState> TERMINAL =
      EnumSet.of(
          SUCCEEDED,
          PARTIALLY_SUCCEEDED,
          COMPENSATED,
          FAILED,
          TIMED_OUT,
          REJECTED,
          CANCELLED);

  public boolean isTerminal() {
    return TERMINAL.contains(this);
  }
}
