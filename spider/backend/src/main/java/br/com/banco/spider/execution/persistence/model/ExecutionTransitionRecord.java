package br.com.banco.spider.execution.persistence.model;

import br.com.banco.spider.execution.domain.ExecutionState;
import java.time.Instant;
import java.util.Objects;

public record ExecutionTransitionRecord(
    String transitionId,
    String executionId,
    long sequence,
    ExecutionState previousState,
    ExecutionState newState,
    String reasonCode,
    Instant occurredAt,
    String attemptId) {

  public ExecutionTransitionRecord {
    Objects.requireNonNull(transitionId, "transitionId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(newState, "newState");
    Objects.requireNonNull(reasonCode, "reasonCode");
    Objects.requireNonNull(occurredAt, "occurredAt");
  }
}
