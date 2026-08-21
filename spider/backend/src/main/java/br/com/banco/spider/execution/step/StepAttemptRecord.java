package br.com.banco.spider.execution.step;

import br.com.banco.spider.canonical.error.ErrorCategory;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record StepAttemptRecord(
    String attemptId,
    String executionId,
    String stepId,
    int attemptNumber,
    String invocationId,
    String adapterBindingRef,
    Instant startedAt,
    Instant deadline,
    Instant completedAt,
    AttemptState state,
    ErrorCategory errorCategory,
    String errorCode,
    Boolean retryable,
    String certainty,
    List<String> evidenceRefs) {

  public StepAttemptRecord {
    Objects.requireNonNull(attemptId, "attemptId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(stepId, "stepId");
    Objects.requireNonNull(invocationId, "invocationId");
    Objects.requireNonNull(adapterBindingRef, "adapterBindingRef");
    Objects.requireNonNull(startedAt, "startedAt");
    Objects.requireNonNull(deadline, "deadline");
    Objects.requireNonNull(state, "state");
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }
}
