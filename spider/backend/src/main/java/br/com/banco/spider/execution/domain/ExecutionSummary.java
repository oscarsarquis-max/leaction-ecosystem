package br.com.banco.spider.execution.domain;

import java.time.Instant;
import java.util.Objects;

public record ExecutionSummary(
    String executionId,
    ExecutionState state,
    Instant startedAt,
    Instant completedAt,
    Instant lastUpdatedAt) {

  public ExecutionSummary {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(lastUpdatedAt, "lastUpdatedAt");
    executionId = executionId.trim();
    if (executionId.isEmpty()) {
      throw new IllegalArgumentException("executionId must not be blank");
    }
  }
}
