package br.com.banco.spider.satellite.contract;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class SatelliteInteractionParser {

  private SatelliteInteractionParser() {}

  public static SatelliteInteractionRequest parse(Map<String, Object> body) {
    if (body == null) {
      return null;
    }
    return new SatelliteInteractionRequest(
        text(body, "contractVersion"),
        text(body, "messageId"),
        text(body, "correlationId"),
        text(body, "satelliteId"),
        text(body, "satelliteRole"),
        text(body, "interactionType"),
        text(body, "createdAt"),
        text(body, "idempotencyKey"),
        text(body, "purpose"),
        parseObjective(body.get("objective")),
        parseContext(body.get("context")),
        text(body, "dataClassification"),
        text(body, "responseChannel"),
        stringMap(body.get("metadata")),
        objectMap(body.get("extensions")));
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> objectMap(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return Map.of();
    }
    return new LinkedHashMap<>((Map<String, Object>) map);
  }

  @SuppressWarnings("unchecked")
  private static SatelliteInteractionRequest.Objective parseObjective(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return null;
    }
    Map<String, Object> typed = (Map<String, Object>) map;
    return new SatelliteInteractionRequest.Objective(
        text(typed, "text"), text(typed, "origin"), text(typed, "declaredAt"));
  }

  @SuppressWarnings("unchecked")
  private static SatelliteInteractionRequest.ContextBlock parseContext(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return null;
    }
    Map<String, Object> typed = (Map<String, Object>) map;
    return new SatelliteInteractionRequest.ContextBlock(
        text(typed, "contextRef"), parseSnapshot(typed.get("snapshot")));
  }

  @SuppressWarnings("unchecked")
  private static SatelliteInteractionRequest.ContextSnapshot parseSnapshot(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return null;
    }
    Map<String, Object> typed = (Map<String, Object>) map;
    Object personal = typed.get("nonPersonal");
    boolean nonPersonal = Boolean.TRUE.equals(personal) || "true".equals(String.valueOf(personal));
    return new SatelliteInteractionRequest.ContextSnapshot(
        text(typed, "schemaVersion"),
        text(typed, "classification"),
        nonPersonal,
        parseProvenance(typed.get("provenance")),
        stringMap(typed.get("attributes")),
        parseContributions(typed.get("contributions")),
        text(typed, "selectedContribution"));
  }

  @SuppressWarnings("unchecked")
  private static List<SatelliteInteractionRequest.Contribution> parseContributions(Object raw) {
    if (!(raw instanceof List<?> list) || list.isEmpty()) {
      return List.of();
    }
    List<SatelliteInteractionRequest.Contribution> values = new ArrayList<>();
    for (Object item : list) {
      if (!(item instanceof Map<?, ?> map)) {
        continue;
      }
      Map<String, Object> typed = (Map<String, Object>) map;
      Object usedRaw = typed.get("used");
      boolean used = Boolean.TRUE.equals(usedRaw) || "true".equals(String.valueOf(usedRaw));
      values.add(
          new SatelliteInteractionRequest.Contribution(
              text(typed, "role"),
              text(typed, "sourceType"),
              text(typed, "sourceId"),
              text(typed, "sourceTimestamp"),
              text(typed, "captureMethod"),
              text(typed, "trustLevel"),
              used,
              stringMap(typed.get("elements"))));
    }
    return values;
  }

  @SuppressWarnings("unchecked")
  private static SatelliteInteractionRequest.Provenance parseProvenance(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return null;
    }
    Map<String, Object> typed = (Map<String, Object>) map;
    return new SatelliteInteractionRequest.Provenance(
        text(typed, "sourceType"),
        text(typed, "sourceId"),
        text(typed, "sourceTimestamp"),
        text(typed, "captureMethod"),
        text(typed, "trustLevel"));
  }

  private static Map<String, String> stringMap(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return Map.of();
    }
    Map<String, String> values = new LinkedHashMap<>();
    for (Map.Entry<?, ?> entry : map.entrySet()) {
      if (entry.getKey() != null && entry.getValue() != null) {
        values.put(String.valueOf(entry.getKey()), String.valueOf(entry.getValue()));
      }
    }
    return values;
  }

  private static String text(Map<String, Object> body, String key) {
    Object value = body.get(key);
    return value == null ? null : String.valueOf(value);
  }
}
