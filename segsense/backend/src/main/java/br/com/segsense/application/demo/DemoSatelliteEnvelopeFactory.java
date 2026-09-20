package br.com.segsense.application.demo;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;

public final class DemoSatelliteEnvelopeFactory {

  private DemoSatelliteEnvelopeFactory() {}

  public static Map<String, Object> build(DemoProtectionDecisionGateway.Command command, String satelliteId) {
    Instant created =
        command.messageCreatedAt() == null ? Instant.now() : command.messageCreatedAt();
    Instant declared =
        command.objectiveDeclaredAt() == null ? created : command.objectiveDeclaredAt();
    String satelliteVersion =
        command.satelliteContractVersion() == null || command.satelliteContractVersion().isBlank()
            ? "1.0"
            : command.satelliteContractVersion();
    String snapshotVersion =
        command.snapshotSchemaVersion() == null || command.snapshotSchemaVersion().isBlank()
            ? ("1.2".equals(satelliteVersion) ? "1.2" : "1.1".equals(satelliteVersion) ? "1.1" : "1.0")
            : command.snapshotSchemaVersion();
    String sourceType =
        command.provenanceSourceType() == null ? "SATELLITE_GOVERNED" : command.provenanceSourceType();
    String captureMethod =
        command.provenanceCaptureMethod() == null ? "SERVER_REGISTRY" : command.provenanceCaptureMethod();
    String trustLevel =
        command.provenanceTrustLevel() == null ? "GOVERNED" : command.provenanceTrustLevel();
    String sourceId =
        command.sourceId() == null || command.sourceId().isBlank()
            ? GovernedDemoOrigin.EDITORIAL_PIECE_KEY
            : command.sourceId();
    String sourceTimestamp = command.provenanceSourceTimestamp();
    if (sourceTimestamp == null || sourceTimestamp.isBlank()) {
      sourceTimestamp =
          "SATELLITE_GOVERNED".equals(sourceType)
              ? GovernedDemoOrigin.CAPTURED_AT
              : created.toString();
    }
    List<Map<String, Object>> contributions = stampContributions(command.contributions(), created);
    Map<String, Object> provenance = new LinkedHashMap<>();
    provenance.put("sourceType", sourceType);
    provenance.put("sourceId", sourceId);
    provenance.put("sourceTimestamp", sourceTimestamp);
    provenance.put("captureMethod", captureMethod);
    provenance.put("trustLevel", trustLevel);
    Map<String, Object> snapshot = new LinkedHashMap<>();
    snapshot.put("schemaVersion", snapshotVersion);
    snapshot.put("classification", "INTERNAL");
    snapshot.put("nonPersonal", true);
    snapshot.put("provenance", provenance);
    if (command.selectedContribution() != null && !command.selectedContribution().isBlank()) {
      snapshot.put("selectedContribution", command.selectedContribution());
    }
    if (!contributions.isEmpty()) {
      snapshot.put("contributions", contributions);
    }
    Map<String, String> attributes = command.contextAttributes();
    if (attributes == null || attributes.isEmpty()) {
      snapshot.put(
          "attributes",
          Map.of(
              "channel", GovernedDemoOrigin.CHANNEL,
              "editorialPieceVersion", GovernedDemoOrigin.EDITORIAL_PIECE_VERSION,
              "purposeVersion", GovernedDemoOrigin.PURPOSE_VERSION));
    } else {
      snapshot.put("attributes", attributes);
    }
    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("contractVersion", satelliteVersion);
    payload.put("messageId", "msg-" + UUID.randomUUID());
    payload.put("correlationId", command.correlationId());
    payload.put("satelliteId", satelliteId);
    payload.put("satelliteRole", "EXPERIENCE");
    payload.put("interactionType", "REQUEST_DECISION");
    payload.put("createdAt", created.toString());
    payload.put("idempotencyKey", command.idempotencyKey());
    payload.put("purpose", "INSURANCE_PROTECTION_ASSESSMENT");
    payload.put(
        "objective",
        Map.of(
            "text",
            command.declaredObjective(),
            "origin",
            command.objectiveOrigin() == null ? "USER_DECLARED" : command.objectiveOrigin(),
            "declaredAt",
            declared.toString()));
    payload.put("context", Map.of("snapshot", snapshot));
    payload.put("dataClassification", "INTERNAL");
    payload.put("responseChannel", "SYNC");
    payload.put("metadata", Map.of());
    return payload;
  }

  @SuppressWarnings("unchecked")
  static List<Map<String, Object>> stampContributions(
      List<Map<String, Object>> contributions, Instant created) {
    if (contributions == null || contributions.isEmpty()) {
      return List.of();
    }
    List<Map<String, Object>> stamped = new ArrayList<>();
    for (Map<String, Object> contribution : contributions) {
      Map<String, Object> copy = new LinkedHashMap<>(contribution);
      Object timestamp = copy.get("sourceTimestamp");
      if (timestamp == null || String.valueOf(timestamp).isBlank()) {
        copy.put("sourceTimestamp", created.toString());
      }
      Object elements = copy.get("elements");
      if (elements instanceof Map<?, ?> map) {
        Map<String, String> typed = new LinkedHashMap<>();
        map.forEach((key, value) -> typed.put(String.valueOf(key), String.valueOf(value)));
        copy.put("elements", typed);
      }
      stamped.add(copy);
    }
    return stamped;
  }
}
