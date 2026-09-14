package br.com.segsense.application.demo;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class DemoSatelliteEnvelopeFactoryTest {

  @Test
  void timestampsAreDistinctFromEditorialFixture() {
    Instant created = Instant.parse("2026-09-14T18:10:00Z");
    Instant declared = Instant.parse("2026-09-14T18:10:05Z");
    DemoProtectionDecisionGateway.Command command =
        new DemoProtectionDecisionGateway.Command(
            "segsense-demo-contract-v1",
            "SEGSENSE",
            DemoDeclaredOrigin.FAMILY_ID,
            "UNDERSTAND_PROTECTION_OPTIONS",
            "11111111-1111-1111-1111-111111111111",
            "idem-ts-1",
            DemoDeclaredOrigin.FAMILY_ID,
            DemoDeclaredOrigin.attributes(DemoDeclaredContextParser.FAMILY),
            "USER_DECLARED",
            created,
            declared,
            "1.1",
            "1.1",
            "USER_DECLARED",
            "SATELLITE_DECLARED",
            "DECLARED",
            created.toString(),
            List.of(DemoDeclaredOrigin.contribution(DemoDeclaredContextParser.FAMILY, true)),
            "VISITOR_DECLARED");
    Map<String, Object> envelope = DemoSatelliteEnvelopeFactory.build(command, "segsense");
    assertEquals("1.1", envelope.get("contractVersion"));
    assertEquals(created.toString(), envelope.get("createdAt"));
    assertEquals(declared.toString(), ((Map<?, ?>) envelope.get("objective")).get("declaredAt"));
    assertNotEquals(GovernedDemoOrigin.CAPTURED_AT, envelope.get("createdAt"));
    assertNotEquals(
        GovernedDemoOrigin.CAPTURED_AT, ((Map<?, ?>) envelope.get("objective")).get("declaredAt"));
    @SuppressWarnings("unchecked")
    Map<String, Object> snapshot =
        (Map<String, Object>) ((Map<String, Object>) envelope.get("context")).get("snapshot");
    @SuppressWarnings("unchecked")
    Map<String, Object> provenance = (Map<String, Object>) snapshot.get("provenance");
    assertEquals("USER_DECLARED", provenance.get("sourceType"));
    assertEquals(created.toString(), provenance.get("sourceTimestamp"));
    assertTrue(snapshot.get("contributions") instanceof List<?>);
  }

  @Test
  void governedEditorialTimestampStaysOnContribution() {
    Instant created = Instant.parse("2026-09-14T18:11:00Z");
    GovernedDemoSource family = GovernedDemoSourceRegistry.family();
    DemoProtectionDecisionGateway.Command command =
        new DemoProtectionDecisionGateway.Command(
            "segsense-demo-contract-v1",
            "SEGSENSE",
            family.id(),
            "UNDERSTAND_PROTECTION_OPTIONS",
            "11111111-1111-1111-1111-111111111111",
            "idem-ts-2",
            family.id(),
            Map.of("channel", GovernedDemoOrigin.CHANNEL, "theme", family.theme(), "constraint", "no_quote", "purposeVersion", GovernedDemoOrigin.PURPOSE_VERSION),
            "USER_DECLARED",
            created,
            created,
            "1.1",
            "1.1",
            "SATELLITE_GOVERNED",
            "SERVER_REGISTRY",
            "GOVERNED",
            family.capturedAt(),
            List.of(DemoDeclaredOrigin.governedContribution(family, true)),
            "GOVERNED_SOURCE");
    Map<String, Object> envelope = DemoSatelliteEnvelopeFactory.build(command, "segsense");
    assertEquals(created.toString(), envelope.get("createdAt"));
    @SuppressWarnings("unchecked")
    Map<String, Object> snapshot =
        (Map<String, Object>) ((Map<String, Object>) envelope.get("context")).get("snapshot");
    @SuppressWarnings("unchecked")
    Map<String, Object> provenance = (Map<String, Object>) snapshot.get("provenance");
    assertEquals(family.capturedAt(), provenance.get("sourceTimestamp"));
    assertNotEquals(created.toString(), provenance.get("sourceTimestamp"));
  }
}
