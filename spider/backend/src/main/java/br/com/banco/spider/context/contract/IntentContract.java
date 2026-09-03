package br.com.banco.spider.context.contract;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Fronteira formal entre interpretação contextual e decisão determinística.
 *
 * <p>O contrato é deliberadamente independente de endpoint, adapter e processor.
 */
public record IntentContract(
    String schemaVersion,
    String intent,
    String domain,
    String objective,
    Map<String, String> entities,
    IntentConstraints constraints,
    IntentProvenance provenance,
    BigDecimal confidence) {

  public IntentContract {
    entities = entities == null ? Map.of() : Map.copyOf(entities);
  }
}
