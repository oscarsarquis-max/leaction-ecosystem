package br.com.banco.spider.canonical.contract;

import br.com.banco.spider.canonical.versioning.VersionedReference;
import java.time.Instant;
import java.util.Objects;

/** Resumo seguro de entrega de callback (PROMPT-007/008). Sem binding físico ou payload. */
public record CallbackDeliverySummary(
    VersionedReference callbackRef,
    String deliveryState,
    int attemptCount,
    Instant lastUpdatedAt,
    String lastErrorCode,
    String confirmationState,
    String reconciliationState,
    int deliveryAttemptCount,
    int reconciliationQueryCount,
    String lastSafeDisposition,
    Instant nextActionAt,
    Instant confirmedAt,
    boolean requiresManualReview) {

  public CallbackDeliverySummary {
    Objects.requireNonNull(callbackRef, "callbackRef");
    Objects.requireNonNull(deliveryState, "deliveryState");
    Objects.requireNonNull(lastUpdatedAt, "lastUpdatedAt");
  }

  /** Compatível com callers PROMPT-007. */
  public CallbackDeliverySummary(
      VersionedReference callbackRef,
      String deliveryState,
      int attemptCount,
      Instant lastUpdatedAt,
      String lastErrorCode) {
    this(
        callbackRef,
        deliveryState,
        attemptCount,
        lastUpdatedAt,
        lastErrorCode,
        null,
        null,
        attemptCount,
        0,
        null,
        null,
        null,
        false);
  }
}
