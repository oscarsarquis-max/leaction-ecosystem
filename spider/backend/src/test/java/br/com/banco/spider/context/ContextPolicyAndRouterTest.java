package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.contract.IntentProvenance;
import br.com.banco.spider.context.contract.IntentProvenanceSource;
import br.com.banco.spider.context.domain.ContextGuardDecision;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import java.math.BigDecimal;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ContextPolicyAndRouterTest {

  private StaticBusinessIntentCatalog catalog;
  private ContextPolicyGuard guard;
  private DeterministicIntentRouter router;
  private IntentContract credit;

  @BeforeEach
  void setUp() {
    catalog = new StaticBusinessIntentCatalog();
    guard = new ContextPolicyGuard(catalog);
    router = new DeterministicIntentRouter(catalog);
    credit = catalog.findByIntent("INVESTIGATE_CREDIT_RELEASE").orElseThrow().businessCardContract();
  }

  @Test
  void catalogHasOneDeterministicSituationForEachInitialDomain() {
    assertEquals(6, catalog.list().size());
    assertEquals(
        6, catalog.list().stream().map(item -> item.domain()).distinct().count());
    assertEquals(1, catalog.list().stream().filter(item -> item.executable()).count());
    assertTrue(
        catalog.list().stream()
            .allMatch(
                item ->
                    item.businessCardContract().confidence().toPlainString().equals("1.0")
                        && item.businessCardContract().provenance().source().name().equals("BUSINESS_CARD")));
  }

  @Test
  void sameContractCatalogAndPolicyResolveToSameRoute() {
    var decisionOne = guard.evaluate(credit, true);
    var decisionTwo = guard.evaluate(credit, true);
    var routeOne = router.resolve(credit, decisionOne).orElseThrow();
    var routeTwo = router.resolve(credit, decisionTwo).orElseThrow();

    assertEquals(routeOne, routeTwo);
    assertEquals("CREDIT_RELEASE_DIAGNOSTIC", routeOne.capabilityRef());
    assertEquals("CREDIT_RELEASE_DIAGNOSTIC_V1", routeOne.routeRef());
    assertEquals("RETRY_THEN_SUCCESS", routeOne.targetOperation());
  }

  @Test
  void unsupportedIntentIsBlockedBeforeRouting() {
    IntentContract unsupported =
        new IntentContract(
            credit.schemaVersion(),
            "UNKNOWN_INTENT",
            credit.domain(),
            credit.objective(),
            credit.entities(),
            credit.constraints(),
            credit.provenance(),
            credit.confidence());
    var decision = guard.evaluate(unsupported, true);
    assertEquals(ContextGuardDecision.UNSUPPORTED_INTENT, decision.decision());
    assertTrue(router.resolve(unsupported, decision).isEmpty());
  }

  @Test
  void missingRequiredEntityIsRejected() {
    IntentContract incomplete =
        new IntentContract(
            credit.schemaVersion(),
            credit.intent(),
            credit.domain(),
            credit.objective(),
            Map.of(),
            credit.constraints(),
            credit.provenance(),
            credit.confidence());
    assertEquals(
        ContextGuardDecision.MISSING_CONTEXT, guard.evaluate(incomplete, true).decision());
  }

  @Test
  void mutationNeverCrossesTheReadOnlyPolicy() {
    IntentContract mutable =
        new IntentContract(
            credit.schemaVersion(),
            credit.intent(),
            credit.domain(),
            credit.objective(),
            credit.entities(),
            new IntentConstraints(true, false, true),
            credit.provenance(),
            credit.confidence());
    var decision = guard.evaluate(mutable, true);
    assertEquals(ContextGuardDecision.POLICY_REJECTED, decision.decision());
    assertEquals("MUTATION_NOT_ALLOWED", decision.reasonCode());
    assertFalse(router.resolve(mutable, decision).isPresent());
  }

  @Test
  void confirmationCannotBeRemovedFromTheContract() {
    IntentContract noConfirmation =
        new IntentContract(
            credit.schemaVersion(),
            credit.intent(),
            credit.domain(),
            credit.objective(),
            credit.entities(),
            new IntentConstraints(false, true, false),
            credit.provenance(),
            credit.confidence());
    var decision = guard.evaluate(noConfirmation, true);
    assertEquals(ContextGuardDecision.POLICY_REJECTED, decision.decision());
    assertEquals("CONFIRMATION_REQUIRED", decision.reasonCode());
  }

  @Test
  void naturalLanguageUsesTheSameGuardAndDeterministicRoute() {
    IntentContract naturalLanguage =
        new IntentContract(
            credit.schemaVersion(),
            credit.intent(),
            credit.domain(),
            credit.objective(),
            credit.entities(),
            credit.constraints(),
            new IntentProvenance(IntentProvenanceSource.NATURAL_LANGUAGE, "context-ai:ctxi-1"),
            new BigDecimal("0.94"));
    var decision = guard.evaluate(naturalLanguage, true);
    assertEquals(ContextGuardDecision.ACCEPTED, decision.decision());
    assertEquals(
        router.resolve(credit, guard.evaluate(credit, true)).orElseThrow().routeRef(),
        router.resolve(naturalLanguage, decision).orElseThrow().routeRef());
  }

  @Test
  void naturalLanguageBelowCentralConfidencePolicyIsAmbiguous() {
    IntentContract uncertain =
        new IntentContract(
            credit.schemaVersion(),
            credit.intent(),
            credit.domain(),
            credit.objective(),
            credit.entities(),
            credit.constraints(),
            new IntentProvenance(IntentProvenanceSource.NATURAL_LANGUAGE, "context-ai:ctxi-2"),
            new BigDecimal("0.79"));
    var decision = guard.evaluate(uncertain, true);
    assertEquals(ContextGuardDecision.AMBIGUOUS, decision.decision());
    assertEquals("AI_CONFIDENCE_BELOW_POLICY", decision.reasonCode());
    assertTrue(router.resolve(uncertain, decision).isEmpty());
  }

  @Test
  void unauthenticatedContractIsNotAuthorized() {
    assertEquals(
        ContextGuardDecision.NOT_AUTHORIZED, guard.evaluate(credit, false).decision());
  }

  @Test
  void unsupportedSchemaIsRejected() {
    IntentContract wrongVersion =
        new IntentContract(
            "2.0",
            credit.intent(),
            credit.domain(),
            credit.objective(),
            credit.entities(),
            credit.constraints(),
            credit.provenance(),
            credit.confidence());
    assertEquals(
        ContextGuardDecision.POLICY_REJECTED, guard.evaluate(wrongVersion, true).decision());
  }
}
