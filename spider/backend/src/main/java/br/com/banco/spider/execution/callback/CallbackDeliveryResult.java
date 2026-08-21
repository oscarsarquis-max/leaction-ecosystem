package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.evidence.reference.EvidenceReference;
import java.time.Instant;
import java.util.List;
import java.util.Objects;

public record CallbackDeliveryResult(
    CallbackDeliveryDisposition disposition,
    CallbackDeliveryCertainty certainty,
    Instant completedAt,
    CanonicalError error,
    List<EvidenceReference> evidenceRefs) {

  public CallbackDeliveryResult {
    Objects.requireNonNull(disposition, "disposition");
    Objects.requireNonNull(certainty, "certainty");
    evidenceRefs = evidenceRefs == null ? List.of() : List.copyOf(evidenceRefs);
  }

  public static CallbackDeliveryResult delivered(Instant completedAt) {
    return new CallbackDeliveryResult(
        CallbackDeliveryDisposition.DELIVERED,
        CallbackDeliveryCertainty.CONFIRMED,
        completedAt,
        null,
        List.of());
  }

  public static CallbackDeliveryResult failed(
      CallbackDeliveryDisposition disposition,
      CallbackDeliveryCertainty certainty,
      Instant completedAt,
      CanonicalError error) {
    return new CallbackDeliveryResult(disposition, certainty, completedAt, error, List.of());
  }
}
