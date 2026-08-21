package br.com.banco.spider.execution.runtime;

import br.com.banco.spider.execution.domain.ExecutionState;
import java.time.Instant;
import java.util.Objects;

public record ExecutionTransition(
    long sequence,
    String executionId,
    String planId,
    ExecutionState fromState,
    ExecutionState toState,
    Instant at,
    String reasonCode) {

  public ExecutionTransition {
    Objects.requireNonNull(executionId, "executionId");
    // fromState may be null only on bootstrap into RECEIVED
    Objects.requireNonNull(toState, "toState");
    Objects.requireNonNull(at, "at");
    Objects.requireNonNull(reasonCode, "reasonCode");
  }
}
