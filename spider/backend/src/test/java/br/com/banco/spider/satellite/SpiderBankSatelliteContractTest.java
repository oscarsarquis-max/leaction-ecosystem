package br.com.banco.spider.satellite;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import br.com.banco.spider.satellite.application.DemoSliceRules;
import br.com.banco.spider.satellite.application.SatelliteInteractionService;
import br.com.banco.spider.satellite.application.SatelliteRegistry;
import br.com.banco.spider.satellite.application.WorkingCapitalPlanProjection;
import br.com.banco.spider.satellite.application.port.ProviderCapabilityPort;
import br.com.banco.spider.satellite.contract.SatelliteContractV1;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextBlock;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.ContextSnapshot;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Objective;
import br.com.banco.spider.satellite.contract.SatelliteInteractionRequest.Provenance;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class SpiderBankSatelliteContractTest {

  private ProviderCapabilityPort providers;
  private SatelliteInteractionService service;

  @BeforeEach
  void setUp() {
    providers = mock(ProviderCapabilityPort.class);
    service = new SatelliteInteractionService(new SatelliteRegistry(SatelliteContractV1Test.properties()), providers, null);
  }

  @Test
  void confirmedWorkingCapitalObjectiveSelectsExistingPlanAndDoesNotDispatchProvider() {
    var outcome = service.interact("spiderbank", request(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-ok")).block();
    assertEquals(200, outcome.status());
    assertEquals("PLAN_IMPEDED", outcome.body().get("status"));
    assertEquals("PRESENT_PLAN_IMPEDIMENTS", outcome.body().get("requiredAction"));
    assertEquals(SatelliteContractV1.WATERMARK_CREDIT, outcome.body().get("watermark"));
    assertFalse(outcome.body().containsKey("planId"));
    assertFalse(outcome.body().containsKey("executionId"));
    @SuppressWarnings("unchecked")
    Map<String, Object> summary = (Map<String, Object>) outcome.body().get("resultSummary");
    assertEquals(SatelliteContractV1.SEEK_WORKING_CAPITAL, summary.get("intent"));
    assertEquals(SatelliteContractV1.WORKING_CAPITAL_PLAN, summary.get("planId"));
    assertEquals(false, summary.get("analysisComplete"));
    assertEquals(false, summary.get("providerDispatched"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> impediments = (List<Map<String, Object>>) summary.get("impediments");
    assertEquals(7, impediments.size());
    assertEquals("IDENTIFY_CUSTOMER", impediments.get(0).get("capabilityId"));
    assertTrue(String.valueOf(impediments.get(0).get("reason")).contains("satélite não identifica o cliente"));
    assertEquals("GET_CUSTOMER_PROFILE", impediments.get(1).get("capabilityId"));
    assertEquals("SIMULATE_WORKING_CAPITAL", impediments.get(5).get("capabilityId"));
    assertEquals("PRESENT_OPTIONS", impediments.get(6).get("capabilityId"));
    String explanation = String.valueOf(outcome.body().get("explanation"));
    assertTrue(explanation.contains("WORKING_CAPITAL_DIAGNOSTIC_V1"));
    assertTrue(explanation.contains("não é recusa de crédito") || explanation.contains("Isso não é recusa de crédito"));
    verify(providers, never()).execute(any());
  }

  @Test
  void satelliteIdentityIsNotTreatedAsCustomerPrincipal() {
    Map<String, Object> summary = WorkingCapitalPlanProjection.project();
    assertEquals(false, summary.get("authenticatedCustomerPrincipal"));
    @SuppressWarnings("unchecked")
    List<Map<String, Object>> steps = (List<Map<String, Object>>) summary.get("steps");
    assertEquals(false, steps.get(0).get("completed"));
    assertEquals("IDENTIFY_CUSTOMER", steps.get(0).get("capabilityId"));
    assertEquals("AVAILABLE", steps.get(0).get("availability"));
  }

  @Test
  void unknownCreditSourceIsRejected() {
    var outcome =
        service.interact("spiderbank", requestWithSource("SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1", "idem-credit-forged")).block();
    assertEquals(400, outcome.status());
    assertEquals("INVALID_PAYLOAD", outcome.errorCode());
    verify(providers, never()).execute(any());
  }

  @Test
  void unknownObjectiveIsRejectedByPolicy() {
    var outcome = service.interact("spiderbank", request("UNDERSTAND_PROTECTION_OPTIONS", "idem-credit-obj")).block();
    assertEquals("REJECTED", outcome.body().get("status"));
    verify(providers, never()).execute(any());
  }

  @Test
  void insuranceSatelliteCannotUseCreditPurpose() {
    SatelliteInteractionRequest spoofed =
        new SatelliteInteractionRequest(
            "1.0",
            "msg-credit-spoof",
            "11111111-1111-1111-1111-111111111111",
            "segsense",
            "EXPERIENCE",
            "REQUEST_DECISION",
            "2026-09-13T12:00:00Z",
            "idem-credit-spoof",
            SatelliteContractV1.PURPOSE_WORKING_CAPITAL,
            new Objective(SatelliteContractV1.SEEK_WORKING_CAPITAL, "USER_DECLARED", "2026-09-13T12:00:00Z"),
            creditContext("SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1"),
            "INTERNAL",
            "SYNC",
            Map.of());
    var outcome = service.interact("segsense", spoofed).block();
    assertEquals(403, outcome.status());
    verify(providers, never()).execute(any());
  }

  @Test
  void idempotentReplayReturnsSameDecisionWithoutProvider() {
    var first = service.interact("spiderbank", request(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-replay")).block();
    var second = service.interact("spiderbank", request(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-replay")).block();
    assertEquals(first.body().get("decisionId"), second.body().get("decisionId"));
    assertEquals("PLAN_IMPEDED", second.body().get("status"));
    verify(providers, never()).execute(any());
  }

  @Test
  void idempotencyConflictWhenBodyChanges() {
    var first = service.interact("spiderbank", request(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-conflict")).block();
    assertEquals(200, first.status());
    var conflict =
        service
            .interact(
                "spiderbank",
                requestWithConstraint(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-conflict", "missing_context"))
            .block();
    assertEquals(409, conflict.status());
    assertEquals("IDEMPOTENCY_CONFLICT", conflict.errorCode());
  }

  @Test
  void missingContextConstraintAsksForSpecificComplement() {
    var outcome =
        service
            .interact(
                "spiderbank",
                requestWithConstraint(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-missing", "missing_context"))
            .block();
    assertEquals("MISSING_CONTEXT", outcome.body().get("status"));
    assertEquals("PROVIDE_CONTEXT", outcome.body().get("requiredAction"));
    verify(providers, never()).execute(any());
  }

  @Test
  void creditRulesNeverFallThroughToInsuranceReady() {
    SatelliteInteractionRequest request = request(SatelliteContractV1.SEEK_WORKING_CAPITAL, "unused");
    DemoSliceRules.Decision decision = DemoSliceRules.evaluate(request);
    assertEquals("PLAN_IMPEDED", decision.status());
    assertNull(decision.capabilityId());
  }

  @Test
  void monitorEventsKeepSpiderbankIdentityWithoutProvider() {
    var captured = new java.util.ArrayList<br.com.banco.spider.operational.events.OperationalEventDraft>();
    var monitored =
        new SatelliteInteractionService(new SatelliteRegistry(SatelliteContractV1Test.properties()), providers, captured::add);
    var result = monitored.interact("spiderbank", request(SatelliteContractV1.SEEK_WORKING_CAPITAL, "idem-credit-monitor")).block();
    assertEquals(200, result.status());
    assertFalse(captured.isEmpty());
    for (var event : captured) {
      assertEquals("spiderbank", event.attributes().toMap().get("originSatellite"));
      assertEquals("SPIDER", event.attributes().toMap().get("currentComponent"));
      assertEquals("NOT_USED", event.attributes().toMap().get("aiUsage"));
    }
    assertTrue(
        captured.stream()
            .anyMatch(
                event ->
                    event.eventType()
                        == br.com.banco.spider.operational.events.OperationalEventType.SATELLITE_RESPONSE_RETURNED));
    assertTrue(
        captured.stream()
            .noneMatch(
                event ->
                    event.eventType()
                        == br.com.banco.spider.operational.events.OperationalEventType.PROVIDER_RESULT_RECEIVED));
  }

  private static SatelliteInteractionRequest request(String objective, String key) {
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "spiderbank",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_WORKING_CAPITAL,
        new Objective(objective, "USER_DECLARED", "2026-09-13T12:00:00Z"),
        creditContext("SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1"),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest requestWithSource(String sourceId, String key) {
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "spiderbank",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_WORKING_CAPITAL,
        new Objective(SatelliteContractV1.SEEK_WORKING_CAPITAL, "USER_DECLARED", "2026-09-13T12:00:00Z"),
        creditContext(sourceId),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static SatelliteInteractionRequest requestWithConstraint(String objective, String key, String constraint) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SPIDERBANK_PUBLIC_DEMO");
    attributes.put("theme", "working_capital");
    attributes.put("constraint", constraint);
    return new SatelliteInteractionRequest(
        "1.0",
        "msg-" + key,
        "11111111-1111-1111-1111-111111111111",
        "spiderbank",
        "EXPERIENCE",
        "REQUEST_DECISION",
        "2026-09-13T12:00:00Z",
        key,
        SatelliteContractV1.PURPOSE_WORKING_CAPITAL,
        new Objective(objective, "USER_DECLARED", "2026-09-13T12:00:00Z"),
        new ContextBlock(
            null,
            new ContextSnapshot(
                "1.0",
                "INTERNAL",
                true,
                new Provenance(
                    "SATELLITE_GOVERNED",
                    "SPIDERBANK_WORKING_CAPITAL_SYNTHETIC_V1",
                    "2026-09-13T12:00:00Z",
                    "SERVER_REGISTRY",
                    "GOVERNED"),
                attributes)),
        "INTERNAL",
        "SYNC",
        Map.of());
  }

  private static ContextBlock creditContext(String sourceId) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", "SPIDERBANK_PUBLIC_DEMO");
    attributes.put("theme", "working_capital");
    return new ContextBlock(
        null,
        new ContextSnapshot(
            "1.0",
            "INTERNAL",
            true,
            new Provenance(
                "SATELLITE_GOVERNED",
                sourceId,
                "2026-09-13T12:00:00Z",
                "SERVER_REGISTRY",
                "GOVERNED"),
            attributes));
  }
}
