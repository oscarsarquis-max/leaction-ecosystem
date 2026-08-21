package br.com.banco.spider.execution.step;

import java.time.Instant;
import java.util.Objects;

public record ExecutionStepRecord(
    String executionId,
    String stepId,
    int orderedPosition,
    StepState state,
    long stateVersion,
    String activeAttemptId,
    String outputResultRef,
    String terminalErrorCode,
    Instant startedAt,
    Instant completedAt,
    Instant lastUpdatedAt) {

  public ExecutionStepRecord {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(stepId, "stepId");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(lastUpdatedAt, "lastUpdatedAt");
  }
}
