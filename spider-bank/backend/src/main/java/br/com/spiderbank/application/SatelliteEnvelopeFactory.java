package br.com.spiderbank.application;

import java.util.LinkedHashMap;
import java.util.Map;

public final class SatelliteEnvelopeFactory {

  public static final String CONTRACT_VERSION = "1.0";
  public static final String SATELLITE_ID = "spiderbank";
  public static final String ROLE = "EXPERIENCE";

  private SatelliteEnvelopeFactory() {}

  public static Map<String, Object> build(SpiderDecisionGateway.Command command) {
    Map<String, Object> envelope = new LinkedHashMap<>();
    envelope.put("contractVersion", CONTRACT_VERSION);
    envelope.put("messageId", command.messageId());
    envelope.put("correlationId", command.correlationId());
    envelope.put("satelliteId", SATELLITE_ID);
    envelope.put("satelliteRole", ROLE);
    envelope.put("interactionType", "REQUEST_DECISION");
    envelope.put("createdAt", command.declaredAt());
    envelope.put("idempotencyKey", command.idempotencyKey());
    envelope.put("purpose", GovernedCreditContext.PURPOSE);
    Map<String, Object> objective = new LinkedHashMap<>();
    objective.put("text", GovernedCreditContext.OBJECTIVE);
    objective.put("origin", "USER_DECLARED");
    objective.put("declaredAt", command.declaredAt());
    envelope.put("objective", objective);
    Map<String, Object> provenance = new LinkedHashMap<>();
    provenance.put("sourceType", "SATELLITE_GOVERNED");
    provenance.put("sourceId", GovernedCreditContext.SOURCE_ID);
    provenance.put("sourceTimestamp", command.declaredAt());
    provenance.put("captureMethod", "SERVER_REGISTRY");
    provenance.put("trustLevel", "GOVERNED");
    Map<String, Object> snapshot = new LinkedHashMap<>();
    snapshot.put("schemaVersion", "1.0");
    snapshot.put("classification", "INTERNAL");
    snapshot.put("nonPersonal", true);
    snapshot.put("provenance", provenance);
    snapshot.put("attributes", command.attributes());
    envelope.put("context", Map.of("snapshot", snapshot));
    envelope.put("dataClassification", "INTERNAL");
    envelope.put("responseChannel", "SYNC");
    envelope.put("metadata", Map.of());
    if (command.extensions() != null && !command.extensions().isEmpty()) {
      envelope.put("extensions", command.extensions());
    }
    return envelope;
  }
}
