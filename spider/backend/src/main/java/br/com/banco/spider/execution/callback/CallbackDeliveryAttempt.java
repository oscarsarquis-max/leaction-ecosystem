package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record CallbackDeliveryAttempt(
    String deliveryId,
    String outboxId,
    String logicalCallbackId,
    int attemptNumber,
    String bindingRef,
    Instant startedAt,
    Instant deadline,
    Instant completedAt,
    CallbackDeliveryAttemptState state,
    CallbackDeliveryCertainty certainty,
    ErrorCategory errorCategory,
    String errorCode,
    Boolean retryable,
    List<EvidenceReference> evidenceRefs) {

  public CallbackDeliveryAttempt {
    Objects.requireNonNull(deliveryId, "deliveryId");
    Objects.requireNonNull(outboxId, "outboxId");
    Objects.requireNonNull(logicalCallbackId, "logicalCallbackId");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(startedAt, "startedAt");
    Objects.requireNonNull(deadline, "deadline");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(certainty, "certainty");
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }
}
