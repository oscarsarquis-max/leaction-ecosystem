package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.contract.IntentProvenance;
import br.com.banco.spider.context.contract.IntentProvenanceSource;
import br.com.banco.spider.context.capability.DeterministicCapabilityResolver;
import br.com.banco.spider.context.capability.StaticBusinessCapabilityCatalog;
import br.com.banco.spider.context.domain.ContextGuardDecision;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import br.com.banco.spider.context.planning.DeterministicExecutionPlanResolver;
import br.com.banco.spider.context.planning.StaticExecutionPlanCatalog;
import java.math.BigDecimal;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ContextPolicyAndRouterTest {

  private StaticBusinessIntentCatalog catalog;
  private ContextPolicyGuard guard;
  private DeterministicIntentRouter router;
  private DeterministicExecutionPlanResolver planResolver;
  private DeterministicCapabilityResolver capabilityResolver;
  private IntentContract credit;

  @BeforeEach
  void setUp() {
    catalog = new StaticBusinessIntentCatalog();
    guard = new ContextPolicyGuard(catalog);
    var capabilityCatalog = new StaticBusinessCapabilityCatalog();
    planResolver =
        new DeterministicExecutionPlanResolver(
            new StaticExecutionPlanCatalog(), capabilityCatalog);
    capabilityResolver = new DeterministicCapabilityResolver(capabilityCatalog);
    router = new DeterministicIntentRouter();
    credit = catalog.findByIntent("INVESTIGATE_CREDIT_RELEASE").orElseThrow().businessCardContract();
  }

  @Test
  void catalogHasOneDeterministicSituationForEachInitialDomain() {
    assertEquals(7, catalog.list().size());
    assertEquals(
        6, catalog.listBusinessCards().stream().map(item -> item.domain()).distinct().count());
    assertEquals(6, catalog.listBusinessCards().size());
    assertTrue(
        catalog.listBusinessCards().stream()
            .allMatch(
                item ->
                    item.businessCardContract().confidence().toPlainString().equals("1.0")
                        && item.businessCardContract().provenance().source().name().equals("BUSINESS_CARD")));
  }

  @Test
  void sameContractCatalogAndPolicyResolveToSameRoute() {
    var decisionOne = guard.evaluate(credit, true);
    var decisionTwo = guard.evaluate(credit, true);
    var planOne = planResolver.resolve(credit, decisionOne).orElseThrow();
    var planTwo = planResolver.resolve(credit, decisionTwo).orElseThrow();
    var routeOne =
        router
            .resolvePrimaryRoute(planOne, capabilityResolver.resolve(planOne), decisionOne)
            .orElseThrow();
    var routeTwo =
        router
            .resolvePrimaryRoute(planTwo, capabilityResolver.resolve(planTwo), decisionTwo)
            .orElseThrow();

    assertEquals(planOne, planTwo);
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
    assertTrue(planResolver.resolve(unsupported, decision).isEmpty());
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
    assertFalse(planResolver.resolve(mutable, decision).isPresent());
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
    var cardPlan = planResolver.resolve(credit, guard.evaluate(credit, true)).orElseThrow();
    var naturalPlan = planResolver.resolve(naturalLanguage, decision).orElseThrow();
    assertEquals(
        router
            .resolvePrimaryRoute(
                cardPlan,
                capabilityResolver.resolve(cardPlan),
                guard.evaluate(credit, true))
            .orElseThrow()
            .routeRef(),
        router
            .resolvePrimaryRoute(
                naturalPlan, capabilityResolver.resolve(naturalPlan), decision)
            .orElseThrow()
            .routeRef());
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
    assertTrue(planResolver.resolve(uncertain, decision).isEmpty());
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
