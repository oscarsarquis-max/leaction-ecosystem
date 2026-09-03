package br.com.banco.spider.context.domain;

import br.com.banco.spider.context.contract.IntentProvenanceSource;
import java.math.BigDecimal;

/** Política centralizada: confiança informa a interpretação, mas nunca autoriza execução. */
public final class ContextConfidencePolicy {

  private final BigDecimal naturalLanguageMinimum;

  public ContextConfidencePolicy(BigDecimal naturalLanguageMinimum) {
    this.naturalLanguageMinimum =
        naturalLanguageMinimum == null ? new BigDecimal("0.80") : naturalLanguageMinimum;
  }

  public Decision evaluate(IntentProvenanceSource source, BigDecimal confidence) {
    if (confidence == null
        || confidence.compareTo(BigDecimal.ZERO) < 0
        || confidence.compareTo(BigDecimal.ONE) > 0) {
      return new Decision(false, "CONFIDENCE_OUT_OF_RANGE");
    }
    if (source == IntentProvenanceSource.BUSINESS_CARD) {
      return confidence.compareTo(BigDecimal.ONE) == 0
          ? new Decision(true, "DETERMINISTIC_CONFIDENCE_ACCEPTED")
          : new Decision(false, "DETERMINISTIC_CONFIDENCE_REQUIRED");
    }
    if (source == IntentProvenanceSource.NATURAL_LANGUAGE) {
      return confidence.compareTo(naturalLanguageMinimum) >= 0
          ? new Decision(true, "AI_CONFIDENCE_ACCEPTED")
          : new Decision(false, "AI_CONFIDENCE_BELOW_POLICY");
    }
    return new Decision(false, "PROVENANCE_NOT_ENABLED");
  }

  public BigDecimal naturalLanguageMinimum() {
    return naturalLanguageMinimum;
  }

  public record Decision(boolean accepted, String reasonCode) {}
}
