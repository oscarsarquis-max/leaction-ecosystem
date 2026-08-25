package br.com.banco.spider.operational.failurelab;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;

/** Resultado seguro de uma observação. Nunca carrega payload nem credencial. */
public record VerificationResult(
    String observationCode,
    VerificationStatus status,
    Instant observedAt,
    String expected,
    String observed,
    Map<String, String> safeReferences,
    String explanation) {

  public VerificationResult {
    Objects.requireNonNull(observationCode, "observationCode");
    Objects.requireNonNull(status, "status");
    expected = expected == null ? "" : expected;
    observed = observed == null ? "" : observed;
    safeReferences = safeReferences == null ? Map.of() : Map.copyOf(safeReferences);
    explanation = explanation == null ? "" : explanation;
  }
}
