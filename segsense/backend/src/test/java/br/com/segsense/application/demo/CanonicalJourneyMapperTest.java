package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.segsense.application.demo.DemoProtectionDecisionGateway.Result;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class CanonicalJourneyMapperTest {

  @Test
  void confirmedReadyRequiresDecisionAndProviderReference() {
    Map<String, Object> node = readyNode("spd-1", "ill-1");
    Result result = CanonicalJourneyMapper.fromSatelliteResponse(node);
    assertTrue(CanonicalJourneyMapper.preProposalConfirmed(result));
    assertEquals("PRE_PROPOSAL_READY", result.status());
    assertEquals("ill-1", result.mockResultId());
    assertEquals("SEGSENSE_PUBLIC_DEMO", result.originProvenance().get("channel"));
    assertEquals(1, result.items().size());
  }

  @Test
  void readyWithoutDecisionIdIsIncompleteAndHidesProviderItems() {
    Map<String, Object> node = readyNode(null, "ill-1");
    Result result = CanonicalJourneyMapper.fromSatelliteResponse(node);
    assertFalse(CanonicalJourneyMapper.preProposalConfirmed(result));
    assertEquals("INCOMPLETE_CANONICAL", result.status());
    assertNull(result.mockResultId());
    assertTrue(result.items().isEmpty());
  }

  @Test
  void readyWithoutProviderReferenceIsIncomplete() {
    Map<String, Object> node = readyNode("spd-1", null);
    Result result = CanonicalJourneyMapper.fromSatelliteResponse(node);
    assertEquals("INCOMPLETE_CANONICAL", result.status());
    assertFalse(result.mockCalled());
    assertTrue(result.items().isEmpty());
  }

  @Test
  void confirmedQuoteRequiresPremiumAndReference() {
    Map<String, Object> summary = new LinkedHashMap<>();
    summary.put("kind", "SYNTHETIC_HOME_QUOTE");
    summary.put("origin", "NON_BINDING_DEMO");
    summary.put("providerReference", "qte-1");
    summary.put("providerId", "insurance-provider-mock");
    summary.put("premiumAnnualCents", 54000);
    summary.put("insuredAmountCents", 30000000);
    Map<String, Object> node = new LinkedHashMap<>();
    node.put("status", "READY");
    node.put("decisionId", "spd-q");
    node.put("capabilityId", "GENERATE_SYNTHETIC_HOME_QUOTE");
    node.put("providerRequestId", "preq-q");
    node.put("resultSummary", summary);
    node.put("watermark", "SIMULAÇÃO DEMONSTRATIVA");
    Result result = CanonicalJourneyMapper.fromSatelliteResponse(node);
    assertTrue(CanonicalJourneyMapper.simulatedQuoteConfirmed(result));
    assertFalse(CanonicalJourneyMapper.preProposalConfirmed(result));
    assertEquals("QUOTE_READY", result.status());
    assertEquals(54000, result.simulatedQuote().get("premiumAnnualCents"));
  }

  @Test
  void omittedProvenanceIsNotFilledFromLocalDefaults() {
    Map<String, Object> node = readyNode("spd-1", "ill-1");
    node.remove("originProvenance");
    Result result = CanonicalJourneyMapper.fromSatelliteResponse(node);
    assertTrue(result.originProvenance().isEmpty());
  }

  private static Map<String, Object> readyNode(String decisionId, String providerReference) {
    Map<String, Object> summary = new LinkedHashMap<>();
    summary.put("providerReference", providerReference);
    summary.put("origin", "ILLUSTRATIVE_NOT_ICATU_CONTRACT");
    summary.put("providerId", "insurance-provider-mock");
    summary.put(
        "items",
        List.of(Map.of("code", "STEP", "title", "Revisar", "kind", "JOURNEY_STEP", "notOfferable", true)));
    summary.put("pendingForHumanReview", List.of("Confirmar."));
    Map<String, Object> provenance = new LinkedHashMap<>();
    provenance.put("sourceType", "SATELLITE_GOVERNED");
    provenance.put("attributes", Map.of("channel", "SEGSENSE_PUBLIC_DEMO"));
    Map<String, Object> node = new LinkedHashMap<>();
    node.put("contractVersion", "1.0");
    node.put("status", "READY");
    node.put("decisionId", decisionId);
    node.put("capabilityId", "BUILD_ILLUSTRATIVE_PROTECTION_SCENARIO");
    node.put("providerRequestId", "preq-1");
    node.put("resultSummary", summary);
    node.put("originProvenance", provenance);
    node.put("spiderPath", "SATELLITE_CONTRACT_V1_THEN_CAPABILITY_RESOLUTION");
    node.put("explanation", "A Spider despachou a capability.");
    node.put("watermark", "DEMONSTRAÇÃO");
    return node;
  }
}
