package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.error.CanonicalError;
import java.time.Duration;
import java.time.Instant;
import java.util.Objects;

public record CallbackDeliveryStatusQueryResult(
    CallbackDeliveryStatusDisposition disposition,
    Instant observedAt,
    String externalDeliveryRef,
    String safeProviderStatusCode,
    Duration retryAfter,
    CanonicalError error,
    String evidenceRef) {

  public CallbackDeliveryStatusQueryResult {
    Objects.requireNonNull(disposition, "disposition");
    Objects.requireNonNull(observedAt, "observedAt");
  }

  public static CallbackDeliveryStatusQueryResult of(
      CallbackDeliveryStatusDisposition disposition, Instant observedAt) {
    return new CallbackDeliveryStatusQueryResult(
        disposition, observedAt, null, null, null, null, null);
  }
}
