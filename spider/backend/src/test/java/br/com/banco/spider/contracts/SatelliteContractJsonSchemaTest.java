package br.com.banco.spider.contracts;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.networknt.schema.JsonSchema;
import com.networknt.schema.JsonSchemaFactory;
import com.networknt.schema.SpecVersion;
import com.networknt.schema.ValidationMessage;
import java.io.InputStream;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

class SatelliteContractJsonSchemaTest {

  private static final ObjectMapper MAPPER = new ObjectMapper();
  private static JsonSchema requestSchema;

  @BeforeAll
  static void load() throws Exception {
    try (InputStream in =
        SatelliteContractJsonSchemaTest.class.getResourceAsStream(
            "/contracts/satellite/1.0/satellite-interaction-request.schema.json")) {
      requestSchema = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(in);
    }
  }

  @Test
  void validExperienceEnvelopePasses() throws Exception {
    Set<ValidationMessage> errors = requestSchema.validate(MAPPER.valueToTree(validEnvelope()));
    assertTrue(errors.isEmpty(), errors::toString);
  }

  @Test
  void intentFieldIsRejected() throws Exception {
    Map<String, Object> body = validEnvelope();
    body.put("intent", "forbidden");
    Set<ValidationMessage> errors = requestSchema.validate(MAPPER.valueToTree(body));
    assertFalse(errors.isEmpty());
  }

  private static java.util.LinkedHashMap<String, Object> validEnvelope() {
    java.util.LinkedHashMap<String, Object> envelope = new java.util.LinkedHashMap<>();
    envelope.put("contractVersion", "1.0");
    envelope.put("messageId", "msg-schema-ok-1");
    envelope.put("correlationId", "11111111-1111-1111-1111-111111111111");
    envelope.put("satelliteId", "segsense");
    envelope.put("satelliteRole", "EXPERIENCE");
    envelope.put("interactionType", "REQUEST_DECISION");
    envelope.put("createdAt", "2026-09-13T12:00:00Z");
    envelope.put("idempotencyKey", "idem-schema-ok-1");
    envelope.put("purpose", "INSURANCE_PROTECTION_ASSESSMENT");
    envelope.put(
        "objective",
        Map.of(
            "text",
            "UNDERSTAND_FAMILY_PROTECTION_OPTIONS",
            "origin",
            "SATELLITE_GOVERNED",
            "declaredAt",
            "2026-09-13T12:00:00Z"));
    envelope.put(
        "context",
        Map.of(
            "snapshot",
            Map.of(
                "schemaVersion",
                "1.0",
                "classification",
                "INTERNAL",
                "nonPersonal",
                true,
                "provenance",
                Map.of(
                    "sourceType",
                    "SATELLITE_GOVERNED",
                    "sourceId",
                    "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1",
                    "sourceTimestamp",
                    "2026-09-13T12:00:00Z",
                    "captureMethod",
                    "SERVER_REGISTRY",
                    "trustLevel",
                    "GOVERNED"))));
    envelope.put("dataClassification", "INTERNAL");
    envelope.put("responseChannel", "SYNC");
    envelope.put("metadata", Map.of());
    return envelope;
  }

  @Test
  void contributionsAreRejectedOnV1Schema() throws Exception {
    Map<String, Object> body = validEnvelope();
    body.put("contributions", java.util.List.of(Map.of("role", "VISITOR_DECLARED")));
    Set<ValidationMessage> errors = requestSchema.validate(MAPPER.valueToTree(body));
    assertFalse(errors.isEmpty());
  }

  @Test
  void version11DeclaredExamplePasses() throws Exception {
    JsonSchema schema11;
    try (InputStream in =
        SatelliteContractJsonSchemaTest.class.getResourceAsStream(
            "/contracts/satellite/1.1/satellite-interaction-request.schema.json")) {
      schema11 = JsonSchemaFactory.getInstance(SpecVersion.VersionFlag.V202012).getSchema(in);
    }
    JsonNode example;
    try (InputStream in =
        SatelliteContractJsonSchemaTest.class.getResourceAsStream(
            "/contracts/satellite/1.1/examples/declared-only.request.json")) {
      example = MAPPER.readTree(in);
    }
    Set<ValidationMessage> errors = schema11.validate(example);
    assertTrue(errors.isEmpty(), errors::toString);
    Set<ValidationMessage> v1Errors = requestSchema.validate(example);
    assertFalse(v1Errors.isEmpty());
  }
}
