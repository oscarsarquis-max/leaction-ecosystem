package br.com.banco.spider.execution.domain;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Objects;

/**
 * Outcome técnico + negócio delegado. Negócio negativo pode coexistir com SUCCESS técnico.
 */
public record CanonicalOutcome(
    TechnicalStatus technicalStatus, JsonNode businessOutcome, JsonNode canonicalData) {

  public CanonicalOutcome {
    Objects.requireNonNull(technicalStatus, "technicalStatus");
  }

  public static CanonicalOutcome technical(TechnicalStatus status) {
    return new CanonicalOutcome(status, null, null);
  }
}
