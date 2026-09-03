package br.com.banco.spider.context.domain;

import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.contract.IntentProvenanceSource;

/** Validação determinística antes de qualquer resolução ou acesso ao Core. */
public final class ContextPolicyGuard {

  public static final String POLICY_REF = "context:read-only@1.0";

  private final BusinessIntentCatalog catalog;
  private final ContextConfidencePolicy confidencePolicy;

  public ContextPolicyGuard(BusinessIntentCatalog catalog) {
    this(catalog, new ContextConfidencePolicy(null));
  }

  public ContextPolicyGuard(
      BusinessIntentCatalog catalog, ContextConfidencePolicy confidencePolicy) {
    this.catalog = catalog;
    this.confidencePolicy = confidencePolicy;
  }

  public GuardResult evaluate(IntentContract contract, boolean authenticated) {
    if (!authenticated) {
      return rejected(ContextGuardDecision.NOT_AUTHORIZED, "CONTEXT_PRINCIPAL_NOT_AUTHENTICATED");
    }
    if (contract == null
        || blank(contract.schemaVersion())
        || blank(contract.intent())
        || blank(contract.domain())
        || blank(contract.objective())
        || contract.constraints() == null
        || contract.provenance() == null
        || contract.provenance().source() == null
        || contract.confidence() == null) {
      return rejected(ContextGuardDecision.MISSING_CONTEXT, "INTENT_CONTRACT_INCOMPLETE");
    }
    if (!"1.0".equals(contract.schemaVersion())) {
      return rejected(ContextGuardDecision.POLICY_REJECTED, "UNSUPPORTED_INTENT_SCHEMA");
    }
    var definition = catalog.findByIntent(contract.intent());
    if (definition.isEmpty()) {
      return rejected(ContextGuardDecision.UNSUPPORTED_INTENT, "INTENT_NOT_IN_CATALOG");
    }
    if (!definition.get().domain().equals(contract.domain())
        || !definition.get().objective().equals(contract.objective())) {
      return rejected(ContextGuardDecision.POLICY_REJECTED, "INTENT_DOMAIN_OBJECTIVE_MISMATCH");
    }
    if (contract.provenance().source() != IntentProvenanceSource.BUSINESS_CARD
        && contract.provenance().source() != IntentProvenanceSource.NATURAL_LANGUAGE) {
      return rejected(ContextGuardDecision.POLICY_REJECTED, "PROVENANCE_NOT_ENABLED");
    }
    ContextConfidencePolicy.Decision confidence =
        confidencePolicy.evaluate(contract.provenance().source(), contract.confidence());
    if (!confidence.accepted()) {
      ContextGuardDecision decision =
          "AI_CONFIDENCE_BELOW_POLICY".equals(confidence.reasonCode())
                  || "DETERMINISTIC_CONFIDENCE_REQUIRED".equals(confidence.reasonCode())
              ? ContextGuardDecision.AMBIGUOUS
              : ContextGuardDecision.POLICY_REJECTED;
      return rejected(decision, confidence.reasonCode());
    }
    if (Boolean.TRUE.equals(contract.constraints().mutationAllowed())
        || !Boolean.TRUE.equals(contract.constraints().readOnly())) {
      return rejected(ContextGuardDecision.POLICY_REJECTED, "MUTATION_NOT_ALLOWED");
    }
    if (!Boolean.TRUE.equals(contract.constraints().confirmationRequired())) {
      return rejected(ContextGuardDecision.POLICY_REJECTED, "CONFIRMATION_REQUIRED");
    }
    boolean missingEntity =
        definition.get().requiredEntityKeys().stream()
            .anyMatch(key -> blank(contract.entities().get(key)));
    if (missingEntity) {
      return rejected(ContextGuardDecision.MISSING_CONTEXT, "REQUIRED_ENTITY_MISSING");
    }
    return new GuardResult(ContextGuardDecision.ACCEPTED, "CONTEXT_POLICY_ACCEPTED", POLICY_REF);
  }

  private static GuardResult rejected(ContextGuardDecision decision, String reasonCode) {
    return new GuardResult(decision, reasonCode, POLICY_REF);
  }

  private static boolean blank(String value) {
    return value == null || value.isBlank();
  }

  public record GuardResult(
      ContextGuardDecision decision, String reasonCode, String policyRef) {
    public boolean accepted() {
      return decision == ContextGuardDecision.ACCEPTED;
    }
  }
}
