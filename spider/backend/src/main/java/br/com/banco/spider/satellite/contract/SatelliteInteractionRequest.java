package br.com.banco.spider.satellite.contract;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

public record SatelliteInteractionRequest(
    String contractVersion,
    String messageId,
    String correlationId,
    String satelliteId,
    String satelliteRole,
    String interactionType,
    String createdAt,
    String idempotencyKey,
    String purpose,
    Objective objective,
    ContextBlock context,
    String dataClassification,
    String responseChannel,
    Map<String, String> metadata) {

  public record Objective(String text, String origin, String declaredAt) {}

  public record Provenance(
      String sourceType, String sourceId, String sourceTimestamp, String captureMethod, String trustLevel) {
    public String fingerprintFragment() {
      return String.join(
          "|",
          nullToEmpty(sourceType),
          nullToEmpty(sourceId),
          nullToEmpty(sourceTimestamp),
          nullToEmpty(captureMethod),
          nullToEmpty(trustLevel));
    }
  }

  public record Contribution(
      String role,
      String sourceType,
      String sourceId,
      String sourceTimestamp,
      String captureMethod,
      String trustLevel,
      boolean used,
      Map<String, String> elements) {
    public String fingerprintFragment() {
      StringBuilder elementsPart = new StringBuilder();
      if (elements != null && !elements.isEmpty()) {
        for (Map.Entry<String, String> entry : new TreeMap<>(elements).entrySet()) {
          elementsPart.append(entry.getKey()).append('=').append(entry.getValue()).append(';');
        }
      }
      return String.join(
          "|",
          nullToEmpty(role),
          nullToEmpty(sourceType),
          nullToEmpty(sourceId),
          nullToEmpty(sourceTimestamp),
          nullToEmpty(captureMethod),
          nullToEmpty(trustLevel),
          Boolean.toString(used),
          elementsPart.toString());
    }

    public Map<String, Object> toMap() {
      Map<String, Object> map = new LinkedHashMap<>();
      map.put("role", role);
      map.put("sourceType", sourceType);
      map.put("sourceId", sourceId);
      map.put("sourceTimestamp", sourceTimestamp);
      map.put("captureMethod", captureMethod);
      map.put("trustLevel", trustLevel);
      map.put("used", used);
      if (elements != null) {
        map.put("elements", elements);
      }
      return map;
    }
  }

  public record ContextSnapshot(
      String schemaVersion,
      String classification,
      boolean nonPersonal,
      Provenance provenance,
      Map<String, String> attributes,
      List<Contribution> contributions,
      String selectedContribution) {

    public ContextSnapshot(
        String schemaVersion,
        String classification,
        boolean nonPersonal,
        Provenance provenance,
        Map<String, String> attributes) {
      this(schemaVersion, classification, nonPersonal, provenance, attributes, List.of(), null);
    }

    public String fingerprintFragment() {
      StringBuilder attributesPart = new StringBuilder();
      if (attributes != null && !attributes.isEmpty()) {
        for (Map.Entry<String, String> entry : new TreeMap<>(attributes).entrySet()) {
          attributesPart.append(entry.getKey()).append('=').append(entry.getValue()).append(';');
        }
      }
      StringBuilder contributionsPart = new StringBuilder();
      if (contributions != null) {
        for (Contribution contribution : contributions) {
          contributionsPart.append(contribution.fingerprintFragment()).append('#');
        }
      }
      return String.join(
          "|",
          nullToEmpty(schemaVersion),
          nullToEmpty(classification),
          Boolean.toString(nonPersonal),
          provenance == null ? "" : provenance.fingerprintFragment(),
          attributesPart.toString(),
          nullToEmpty(selectedContribution),
          contributionsPart.toString());
    }
  }

  public record ContextBlock(String contextRef, ContextSnapshot snapshot) {}

  public String semanticFingerprint() {
    String objectiveText = objective == null ? "" : nullToEmpty(objective.text());
    String objectiveOrigin = objective == null ? "" : nullToEmpty(objective.origin());
    String contextPart = "";
    if (context != null && context.snapshot() != null) {
      contextPart = context.snapshot().fingerprintFragment();
    } else if (context != null) {
      contextPart = nullToEmpty(context.contextRef());
    }
    return String.join(
        "|",
        nullToEmpty(contractVersion),
        nullToEmpty(satelliteId),
        nullToEmpty(satelliteRole),
        nullToEmpty(interactionType),
        nullToEmpty(purpose),
        objectiveText,
        objectiveOrigin,
        contextPart);
  }

  public Map<String, Object> provenanceMap() {
    ContextSnapshot snapshot = context == null ? null : context.snapshot();
    if (snapshot == null || snapshot.provenance() == null) {
      return Map.of();
    }
    Provenance provenance = snapshot.provenance();
    Map<String, Object> map = new LinkedHashMap<>();
    map.put("sourceType", provenance.sourceType());
    map.put("sourceId", provenance.sourceId());
    map.put("sourceTimestamp", provenance.sourceTimestamp());
    map.put("captureMethod", provenance.captureMethod());
    map.put("trustLevel", provenance.trustLevel());
    map.put("nonPersonal", snapshot.nonPersonal());
    if (snapshot.selectedContribution() != null) {
      map.put("selectedContribution", snapshot.selectedContribution());
    }
    if (snapshot.attributes() != null) {
      map.put("attributes", snapshot.attributes());
    }
    if (snapshot.contributions() != null && !snapshot.contributions().isEmpty()) {
      List<Map<String, Object>> rows = new ArrayList<>();
      for (Contribution contribution : snapshot.contributions()) {
        rows.add(contribution.toMap());
      }
      map.put("contributions", rows);
    }
    return map;
  }

  private static String nullToEmpty(String value) {
    return value == null ? "" : value;
  }
}
