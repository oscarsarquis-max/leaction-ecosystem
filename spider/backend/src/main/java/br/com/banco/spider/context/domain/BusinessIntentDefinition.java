package br.com.banco.spider.context.domain;

import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.contract.IntentProvenance;
import br.com.banco.spider.context.contract.IntentProvenanceSource;
import java.math.BigDecimal;
import java.util.Map;
import java.util.Set;

/** Entrada determinística do catálogo de situações de negócio. */
public record BusinessIntentDefinition(
    String domain,
    String domainLabel,
    String intent,
    String objective,
    String title,
    String description,
    Set<String> allowedEntityKeys,
    Set<String> requiredEntityKeys,
    Map<String, String> demoEntities,
    boolean businessCardEnabled) {

  public BusinessIntentDefinition {
    allowedEntityKeys = Set.copyOf(allowedEntityKeys);
    requiredEntityKeys = Set.copyOf(requiredEntityKeys);
    demoEntities = Map.copyOf(demoEntities);
  }

  public IntentContract businessCardContract() {
    if (!businessCardEnabled) {
      throw new IllegalStateException("Intent is not exposed as a Business Intent Card");
    }
    return new IntentContract(
        "1.0",
        intent,
        domain,
        objective,
        demoEntities,
        IntentConstraints.readOnlyWithConfirmation(),
        new IntentProvenance(IntentProvenanceSource.BUSINESS_CARD, "context-catalog:" + intent),
        new BigDecimal("1.0"));
  }
}
