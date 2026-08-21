package br.com.banco.spider.execution.runtime;

import br.com.banco.spider.execution.domain.ExecutionState;

public final class InvalidStateTransitionException extends RuntimeException {

  private final ExecutionState from;
  private final ExecutionState to;

  public InvalidStateTransitionException(ExecutionState from, ExecutionState to, String detail) {
    super("Invalid transition " + from + " → " + to + ": " + detail);
    this.from = from;
    this.to = to;
  }

  public ExecutionState from() {
    return from;
  }

  public ExecutionState to() {
    return to;
  }
}
