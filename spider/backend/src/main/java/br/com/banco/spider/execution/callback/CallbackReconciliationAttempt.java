package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.error.CanonicalError;
import java.time.Instant;
import java.util.Objects;

public record CallbackReconciliationAttempt(
    String reconciliationAttemptId,
    String reconciliationId,
    int attemptNumber,
    Instant startedAt,
    Instant completedAt,
    CallbackDeliveryStatusDisposition disposition,
    String safeStatusCode,
    CanonicalError canonicalError,
    Instant nextQueryAt,
    String evidenceRef,
    String traceCorrelationId) {

  public CallbackReconciliationAttempt {
    Objects.requireNonNull(reconciliationAttemptId, "reconciliationAttemptId");
    Objects.requireNonNull(reconciliationId, "reconciliationId");
    Objects.requireNonNull(startedAt, "startedAt");
  }
}
