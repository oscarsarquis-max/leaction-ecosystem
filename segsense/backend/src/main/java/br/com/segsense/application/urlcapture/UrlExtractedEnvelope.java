package br.com.segsense.application.urlcapture;

import br.com.segsense.application.demo.DemoProjectionJson;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class UrlExtractedEnvelope {

  public static final String DECLARED_CORRECTION_ID = "SEGSENSE_DECLARED_URL_CORRECTION_V1";
  public static final String CHANNEL = "SEGSENSE_PUBLIC_DEMO";
  public static final String ORIGIN_EXTRACTED = "URL_EXTRACTED";
  public static final String ORIGIN_DECLARED = "USER_DECLARED";

  private UrlExtractedEnvelope() {}

  public static String sourceId(String textSha256) {
    String hash = textSha256 == null ? "" : textSha256;
    String prefix = hash.length() >= 32 ? hash.substring(0, 32) : hash + "0".repeat(32 - hash.length());
    return "SEGSENSE_URL_" + prefix;
  }

  public static Map<String, Object> urlContribution(UrlCaptureRecord capture, List<Map<String, String>> extracted) {
    Map<String, Object> contribution = new LinkedHashMap<>();
    contribution.put("role", "URL_EXTRACTED");
    contribution.put("sourceType", "URL_EXTRACTED");
    contribution.put("sourceId", sourceId(capture.textSha256()));
    contribution.put("sourceTimestamp", capture.capturedAt() == null ? null : capture.capturedAt().toString());
    contribution.put("captureMethod", "SERVER_FETCH");
    contribution.put("trustLevel", "OBSERVED");
    contribution.put("used", true);
    contribution.put("elements", compactElements(supportedUrlExtracted(capture, extracted), ORIGIN_EXTRACTED));
    return contribution;
  }

  public static Map<String, Object> correctionContribution(List<Map<String, String>> declared) {
    Map<String, Object> contribution = new LinkedHashMap<>();
    contribution.put("role", "VISITOR_DECLARED");
    contribution.put("sourceType", "USER_DECLARED");
    contribution.put("sourceId", DECLARED_CORRECTION_ID);
    contribution.put("captureMethod", "SATELLITE_DECLARED");
    contribution.put("trustLevel", "DECLARED");
    contribution.put("used", true);
    contribution.put("elements", compactElements(declared, ORIGIN_DECLARED));
    return contribution;
  }

  public static Map<String, String> attributes(List<Map<String, String>> confirmed) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", CHANNEL);
    putIfPresent(attributes, confirmed, "theme");
    putIfPresent(attributes, confirmed, "situation");
    putIfPresent(attributes, confirmed, "constraint");
    if (!attributes.containsKey("constraint")) {
      attributes.put("constraint", attributes.containsKey("theme") ? "editorial_not_eligibility" : "missing_context");
    }
    return attributes;
  }

  public static List<Map<String, String>> supportedUrlExtracted(
      UrlCaptureRecord capture, List<Map<String, String>> claimed) {
    List<Map<String, String>> original = readElementList(capture == null ? null : capture.extractedElementsJson());
    String text = capture == null || capture.normalizedText() == null ? "" : capture.normalizedText();
    String version = capture == null ? "" : String.valueOf(capture.extractorVersion());
    List<Map<String, String>> supported = new ArrayList<>();
    if (claimed == null) {
      return supported;
    }
    for (Map<String, String> item : claimed) {
      if (!ORIGIN_EXTRACTED.equals(item.get("origin"))) {
        continue;
      }
      Map<String, String> match = findOriginal(original, item.get("key"));
      if (match == null) {
        continue;
      }
      if (!same(match.get("value"), item.get("value"))) {
        continue;
      }
      if (!evidenceSupported(text, match, version)) {
        continue;
      }
      supported.add(match);
    }
    return supported;
  }

  public static boolean evidenceSupported(String normalizedText, Map<String, String> element, String extractorVersion) {
    if (element == null) {
      return false;
    }
    String evidence = element.get("evidence");
    String value = element.get("value");
    if (evidence == null || evidence.isBlank() || value == null || value.isBlank()) {
      return false;
    }
    String text = normalizedText == null ? "" : normalizedText;
    if (!text.contains(evidence)) {
      return false;
    }
    int start = parseOffset(element.get("startOffset"), -1);
    int end = parseOffset(element.get("endOffset"), -1);
    if (start >= 0 && end > start && end <= text.length()) {
      String slice = text.substring(start, end);
      String lowerEvidence = evidence.toLowerCase();
      String lowerSlice = slice.toLowerCase();
      if (!lowerEvidence.contains(lowerSlice) && !value.equalsIgnoreCase(slice.trim())) {
        return false;
      }
    }
    return extractorVersion == null
        || extractorVersion.isBlank()
        || extractorVersion.startsWith("URL_EXTRACTOR_V");
  }

  public static String readSelectionStrategy(String json) {
    if (json == null || json.isBlank()) {
      return "";
    }
    try {
      Map<String, Object> root = DemoProjectionJson.readObject(json);
      Object value = root.get("selectionStrategy");
      return value == null ? "" : String.valueOf(value);
    } catch (RuntimeException ignored) {
      return "";
    }
  }

  @SuppressWarnings("unchecked")
  public static List<Map<String, String>> readElementList(String json) {
    if (json == null || json.isBlank()) {
      return List.of();
    }
    try {
      Map<String, Object> root = DemoProjectionJson.readObject(json);
      Object array = root.get("elements");
      if (!(array instanceof List<?> list)) {
        return List.of();
      }
      List<Map<String, String>> items = new ArrayList<>();
      for (Object raw : list) {
        if (!(raw instanceof Map<?, ?> map)) {
          continue;
        }
        Map<String, String> item = new LinkedHashMap<>();
        copy(item, map, "key");
        copy(item, map, "value");
        copy(item, map, "evidence");
        copy(item, map, "origin");
        copy(item, map, "rule");
        copy(item, map, "startOffset");
        copy(item, map, "endOffset");
        copy(item, map, "windowKind");
        items.add(item);
      }
      return items;
    } catch (RuntimeException ignored) {
      return List.of();
    }
  }

  public static String writeElements(List<Map<String, String>> elements) {
    return DemoProjectionJson.write(Map.of("elements", elements == null ? List.of() : elements));
  }

  private static void copy(Map<String, String> item, Map<?, ?> map, String key) {
    Object value = map.get(key);
    item.put(key, value == null ? "" : String.valueOf(value));
  }

  private static Map<String, String> findOriginal(List<Map<String, String>> original, String key) {
    if (key == null) {
      return null;
    }
    for (Map<String, String> item : original) {
      if (key.equals(item.get("key"))) {
        return item;
      }
    }
    return null;
  }

  private static boolean same(String left, String right) {
    return left != null && left.equals(right);
  }

  private static int parseOffset(String raw, int fallback) {
    if (raw == null || raw.isBlank()) {
      return fallback;
    }
    try {
      return Integer.parseInt(raw.trim());
    } catch (NumberFormatException ignored) {
      return fallback;
    }
  }

  private static Map<String, String> compactElements(List<Map<String, String>> items, String originFilter) {
    Map<String, String> elements = new LinkedHashMap<>();
    if (items == null) {
      return elements;
    }
    for (Map<String, String> item : items) {
      if (originFilter != null && !originFilter.equals(item.get("origin"))) {
        continue;
      }
      String key = item.get("key");
      String value = item.get("value");
      if (key == null || key.isBlank() || value == null || value.isBlank()) {
        continue;
      }
      if (elements.size() >= 8) {
        break;
      }
      elements.put(key, value.length() > 200 ? value.substring(0, 200) : value);
    }
    return elements;
  }

  private static void putIfPresent(Map<String, String> attributes, List<Map<String, String>> items, String key) {
    for (Map<String, String> item : items) {
      if (key.equals(item.get("key")) && item.get("value") != null && !item.get("value").isBlank()) {
        attributes.put(key, item.get("value"));
        return;
      }
    }
  }
}
