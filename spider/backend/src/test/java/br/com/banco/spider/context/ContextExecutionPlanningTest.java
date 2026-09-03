package br.com.banco.spider.context;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.context.capability.CapabilityAvailability;
import br.com.banco.spider.context.capability.CapabilityResolutionStatus;
import br.com.banco.spider.context.capability.DeterministicCapabilityResolver;
import br.com.banco.spider.context.capability.StaticBusinessCapabilityCatalog;
import br.com.banco.spider.context.contract.IntentConstraints;
import br.com.banco.spider.context.contract.IntentContract;
import br.com.banco.spider.context.contract.IntentProvenance;
import br.com.banco.spider.context.contract.IntentProvenanceSource;
import br.com.banco.spider.context.domain.ContextPolicyGuard;
import br.com.banco.spider.context.domain.DeterministicIntentRouter;
import br.com.banco.spider.context.domain.StaticBusinessIntentCatalog;
import br.com.banco.spider.context.planning.ContextExecutionPlanStatus;
import br.com.banco.spider.context.planning.DeterministicExecutionPlanResolver;
import br.com.banco.spider.context.planning.StaticExecutionPlanCatalog;
import java.math.BigDecimal;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class ContextExecutionPlanningTest {

  private StaticBusinessIntentCatalog intents;
  private StaticBusinessCapabilityCatalog capabilities;
  private ContextPolicyGuard guard;
  private DeterministicExecutionPlanResolver plans;
  private DeterministicCapabilityResolver capabilityResolver;

  @BeforeEach
  void setUp() {
    intents = new StaticBusinessIntentCatalog();
    capabilities = new StaticBusinessCapabilityCatalog();
    guard = new ContextPolicyGuard(intents);
    plans =
        new DeterministicExecutionPlanResolver(
            new StaticExecutionPlanCatalog(), capabilities);
    capabilityResolver = new DeterministicCapabilityResolver(capabilities);
  }

  @Test
  void sameValidatedIntentCatalogAndPolicyProduceExactlyTheSamePlan() {
    IntentContract contract = workingCapital(Map.of("purpose", "INVENTORY", "amount", "50000"));
    var policy = guard.evaluate(contract, true);

    var first = plans.resolve(contract, policy).orElseThrow();
    var second = plans.resolve(contract, policy).orElseThrow();

    assertEquals(first, second);
    assertEquals("WORKING_CAPITAL_DIAGNOSTIC_V1", first.planType());
    assertEquals(ContextExecutionPlanStatus.PARTIALLY_AVAILABLE, first.status());
    assertEquals(7, first.steps().size());
    assertTrue(
        first.steps().stream()
            .allMatch(
                step ->
                    step.capabilityId() != null
                        && step.condition() == null
                        && !step.capabilityId().contains("ROUTE")));
  }

  @Test
  void workingCapitalIsPartialAndNeverPretendsUnavailableCapabilitiesExecuted() {
    IntentContract contract = workingCapital(Map.of("purpose", "CASH_FLOW"));
    var plan = plans.resolve(contract, guard.evaluate(contract, true)).orElseThrow();
    var resolutions = capabilityResolver.resolve(plan);

    assertEquals(CapabilityResolutionStatus.RESOLVED, resolutions.getFirst().status());
    assertEquals("IDENTIFY_CUSTOMER", resolutions.getFirst().capabilityId());
    assertEquals(
        CapabilityAvailability.NOT_AVAILABLE, resolutions.get(1).availability());
    assertEquals(6, resolutions.stream().filter(r -> r.status() == CapabilityResolutionStatus.UNAVAILABLE).count());
    assertTrue(
        new DeterministicIntentRouter()
            .resolvePrimaryRoute(plan, resolutions, guard.evaluate(contract, true))
            .isEmpty());
  }

  @Test
  void previousCreditIntentRemainsReadyAndExecutableThroughCapabilityResolution() {
    IntentContract credit =
        intents
            .findByIntent("INVESTIGATE_CREDIT_RELEASE")
            .orElseThrow()
            .businessCardContract();
    var policy = guard.evaluate(credit, true);
    var plan = plans.resolve(credit, policy).orElseThrow();
    var resolutions = capabilityResolver.resolve(plan);
    var route =
        new DeterministicIntentRouter()
            .resolvePrimaryRoute(plan, resolutions, policy)
            .orElseThrow();

    assertEquals(ContextExecutionPlanStatus.READY, plan.status());
    assertEquals("CREDIT_RELEASE_DIAGNOSTIC", resolutions.getFirst().capabilityId());
    assertEquals("CREDIT_RELEASE_DIAGNOSTIC_V1", route.routeRef());
    assertTrue(route.executable());
  }

  @Test
  void missingPurposeIsRejectedBeforePlanResolutionAndAmountRemainsOptional() {
    IntentContract missingPurpose = workingCapital(Map.of("amount", "50000"));
    var rejected = guard.evaluate(missingPurpose, true);
    assertFalse(rejected.accepted());
    assertTrue(plans.resolve(missingPurpose, rejected).isEmpty());

    IntentContract noAmount = workingCapital(Map.of("purpose", "RAW_MATERIAL"));
    var accepted = guard.evaluate(noAmount, true);
    assertTrue(accepted.accepted());
    assertNull(noAmount.entities().get("amount"));
    assertTrue(plans.resolve(noAmount, accepted).isPresent());
  }

  private static IntentContract workingCapital(Map<String, String> entities) {
    return new IntentContract(
        "1.0",
        "SEEK_WORKING_CAPITAL",
        "CREDIT",
        "ASSESS_WORKING_CAPITAL_OPTIONS",
        entities,
        IntentConstraints.readOnlyWithConfirmation(),
        new IntentProvenance(IntentProvenanceSource.NATURAL_LANGUAGE, "context-ai:test"),
        new BigDecimal("0.94"));
  }
}
