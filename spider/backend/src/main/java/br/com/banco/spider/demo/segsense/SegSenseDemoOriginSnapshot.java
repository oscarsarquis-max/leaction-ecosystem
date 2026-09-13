package br.com.banco.spider.demo.segsense;

import java.util.LinkedHashMap;
import java.util.Map;

/** Governed synthetic context. Not personal data, not a Satellite Contract payload. */
public record SegSenseDemoOriginSnapshot(
    String schemaVersion,
    String channel,
    String editorialPieceKey,
    String editorialPieceVersion,
    String purposeVersion,
    String purpose,
    String capturedAt,
    boolean nonPersonal) {

  public static final String SCHEMA_VERSION = "origin-snapshot-v1";
  public static final String CHANNEL = "SEGSENSE_PUBLIC_DEMO";
  public static final String EDITORIAL_PIECE_KEY = "SEGSENSE_FAMILY_CONTINUITY_SYNTHETIC_V1";
  public static final String EDITORIAL_PIECE_VERSION = "demo-editorial-v1";
  public static final String PURPOSE_VERSION = "demo-purpose-v1";
  public static final String PURPOSE =
      "Apresentar jornada ilustrativa de proteção familiar, sem cotação.";
  public static final String CAPTURED_AT = "2026-09-13T12:00:00Z";

  public static SegSenseDemoOriginSnapshot governed() {
    return new SegSenseDemoOriginSnapshot(
        SCHEMA_VERSION,
        CHANNEL,
        EDITORIAL_PIECE_KEY,
        EDITORIAL_PIECE_VERSION,
        PURPOSE_VERSION,
        PURPOSE,
        CAPTURED_AT,
        true);
  }

  public static SegSenseDemoOriginSnapshot parse(Object raw) {
    if (!(raw instanceof Map<?, ?> map)) {
      return null;
    }
    Object personal = map.get("nonPersonal");
    boolean nonPersonalFlag = Boolean.TRUE.equals(personal) || "true".equals(String.valueOf(personal));
    return new SegSenseDemoOriginSnapshot(
        text(map, "schemaVersion"),
        text(map, "channel"),
        text(map, "editorialPieceKey"),
        text(map, "editorialPieceVersion"),
        text(map, "purposeVersion"),
        text(map, "purpose"),
        text(map, "capturedAt"),
        nonPersonalFlag);
  }

  public String validateAgainst(String scenarioKey) {
    if (!SCHEMA_VERSION.equals(schemaVersion)) {
      return "Versão de contexto sintético inválida.";
    }
    if (!CHANNEL.equals(channel)) {
      return "Origem sintética não permitida nesta fatia.";
    }
    if (!EDITORIAL_PIECE_KEY.equals(editorialPieceKey) || !EDITORIAL_PIECE_KEY.equals(scenarioKey)) {
      return "A peça editorial não corresponde ao cenário sintético.";
    }
    if (!EDITORIAL_PIECE_VERSION.equals(editorialPieceVersion)) {
      return "Versão da peça editorial não permitida.";
    }
    if (!PURPOSE_VERSION.equals(purposeVersion) || !PURPOSE.equals(purpose)) {
      return "Finalidade aprovada para a demonstração não conferida.";
    }
    if (!CAPTURED_AT.equals(capturedAt)) {
      return "Instantâneo de contexto não conferido.";
    }
    if (!nonPersonal) {
      return "O contexto desta demonstração precisa ser não pessoal.";
    }
    return null;
  }

  public String fingerprintFragment() {
    return String.join(
        "|",
        nullToEmpty(schemaVersion),
        nullToEmpty(channel),
        nullToEmpty(editorialPieceKey),
        nullToEmpty(editorialPieceVersion),
        nullToEmpty(purposeVersion),
        nullToEmpty(purpose),
        nullToEmpty(capturedAt),
        Boolean.toString(nonPersonal));
  }

  public Map<String, Object> toMap() {
    Map<String, Object> map = new LinkedHashMap<>();
    map.put("schemaVersion", schemaVersion);
    map.put("channel", channel);
    map.put("editorialPieceKey", editorialPieceKey);
    map.put("editorialPieceVersion", editorialPieceVersion);
    map.put("purposeVersion", purposeVersion);
    map.put("purpose", purpose);
    map.put("capturedAt", capturedAt);
    map.put("nonPersonal", nonPersonal);
    return map;
  }

  private static String text(Map<?, ?> map, String key) {
    Object value = map.get(key);
    return value == null ? null : String.valueOf(value);
  }

  private static String nullToEmpty(String value) {
    return value == null ? "" : value;
  }
}
