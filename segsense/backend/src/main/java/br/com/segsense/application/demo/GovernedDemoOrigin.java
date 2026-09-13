package br.com.segsense.application.demo;

import java.util.LinkedHashMap;
import java.util.Map;

/** Server-side governed snapshot. Never taken from the browser. */
public final class GovernedDemoOrigin {

  public static final String SCHEMA_VERSION = "origin-snapshot-v1";
  public static final String CHANNEL = "SEGSENSE_PUBLIC_DEMO";
  public static final String EDITORIAL_PIECE_KEY = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  public static final String EDITORIAL_PIECE_VERSION = "demo-editorial-v1";
  public static final String PURPOSE_VERSION = "demo-purpose-v1";
  public static final String PURPOSE =
      "Apresentar jornada ilustrativa de proteção familiar, sem cotação.";
  public static final String CAPTURED_AT = "2026-09-13T12:00:00Z";

  private GovernedDemoOrigin() {}

  public static Map<String, Object> snapshot() {
    Map<String, Object> map = new LinkedHashMap<>();
    map.put("schemaVersion", SCHEMA_VERSION);
    map.put("channel", CHANNEL);
    map.put("editorialPieceKey", EDITORIAL_PIECE_KEY);
    map.put("editorialPieceVersion", EDITORIAL_PIECE_VERSION);
    map.put("purposeVersion", PURPOSE_VERSION);
    map.put("purpose", PURPOSE);
    map.put("capturedAt", CAPTURED_AT);
    map.put("nonPersonal", true);
    return map;
  }
}
