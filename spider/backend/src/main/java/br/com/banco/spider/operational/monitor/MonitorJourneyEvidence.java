package br.com.banco.spider.operational.monitor;

import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

public final class MonitorJourneyEvidence {

  private static final Set<String> ALLOWED =
      Set.of(
          "eventType",
          "outcome",
          "occurredAt",
          "source",
          "component",
          "executor",
          "decision",
          "page",
          "capability",
          "foundCount",
          "newCount",
          "updatedCount",
          "syncRunId",
          "reason",
          "participation",
          "componentCode",
          "macroStage");

  private MonitorJourneyEvidence() {}

  public static String append(String currentJson, Map<String, String> incoming) {
    List<Map<String, String>> items = parse(currentJson);
    Map<String, String> sanitized = sanitize(incoming);
    if (sanitized.isEmpty()) {
      return write(items);
    }
    String key = sanitized.getOrDefault("eventType", "") + "|" + sanitized.getOrDefault("occurredAt", "");
    boolean exists =
        items.stream()
            .anyMatch(
                item ->
                    (item.getOrDefault("eventType", "") + "|" + item.getOrDefault("occurredAt", "")).equals(key));
    if (!exists) {
      items.add(sanitized);
    }
    if (items.size() > 12) {
      items = items.subList(items.size() - 12, items.size());
    }
    return write(items);
  }

  public static List<Map<String, String>> parse(String json) {
    List<Map<String, String>> items = new ArrayList<>();
    if (json == null || json.isBlank() || "[]".equals(json.trim())) {
      return items;
    }
    String body = json.trim();
    if (!body.startsWith("[") || !body.endsWith("]")) {
      return items;
    }
    String inner = body.substring(1, body.length() - 1).trim();
    if (inner.isEmpty()) {
      return items;
    }
    for (String object : inner.split("(?<=\\}),\\s*(?=\\{)")) {
      Map<String, String> row = new LinkedHashMap<>();
      String cleaned = object.trim();
      if (cleaned.startsWith("{")) {
        cleaned = cleaned.substring(1);
      }
      if (cleaned.endsWith("}")) {
        cleaned = cleaned.substring(0, cleaned.length() - 1);
      }
      for (String pair : cleaned.split(",")) {
        String[] parts = pair.split(":", 2);
        if (parts.length != 2) {
          continue;
        }
        String key = unquote(parts[0]);
        String value = unquote(parts[1]);
        if (ALLOWED.contains(key) && value != null && !value.isBlank()) {
          row.put(key, value);
        }
      }
      if (!row.isEmpty()) {
        items.add(row);
      }
    }
    return items;
  }

  public static Map<String, String> sanitize(Map<String, String> incoming) {
    Map<String, String> clean = new LinkedHashMap<>();
    if (incoming == null) {
      return clean;
    }
    incoming.forEach(
        (key, value) -> {
          if (key == null || value == null || !ALLOWED.contains(key)) {
            return;
          }
          String trimmed = value.trim();
          if (trimmed.isEmpty()) {
            return;
          }
          String lower = trimmed.toLowerCase(Locale.ROOT);
          if (lower.contains("token") || lower.contains("secret") || lower.contains("password")
              || lower.contains("cookie") || lower.contains("authorization")
              || lower.contains("stack")) {
            return;
          }
          clean.put(key, trimmed.length() > 160 ? trimmed.substring(0, 160) : trimmed);
        });
    return clean;
  }

  public static String occurred(Instant value) {
    return value == null ? null : value.toString();
  }

  private static String write(List<Map<String, String>> items) {
    StringBuilder json = new StringBuilder("[");
    for (int i = 0; i < items.size(); i++) {
      if (i > 0) {
        json.append(',');
      }
      json.append('{');
      int field = 0;
      for (Map.Entry<String, String> entry : items.get(i).entrySet()) {
        if (field++ > 0) {
          json.append(',');
        }
        json.append('"').append(escape(entry.getKey())).append("\":\"").append(escape(entry.getValue())).append('"');
      }
      json.append('}');
    }
    json.append(']');
    String result = json.toString();
    return result.length() > 4000 ? result.substring(0, 3990) + "]}" : result;
  }

  private static String unquote(String value) {
    String trimmed = value == null ? "" : value.trim();
    if (trimmed.length() >= 2 && trimmed.startsWith("\"") && trimmed.endsWith("\"")) {
      return trimmed.substring(1, trimmed.length() - 1).replace("\\\"", "\"").replace("\\\\", "\\");
    }
    return trimmed;
  }

  private static String escape(String value) {
    return value.replace("\\", "\\\\").replace("\"", "\\\"");
  }
}
