package br.com.segsense.application.demo;

import java.util.LinkedHashMap;
import java.util.Map;

public final class DemoDeclaredOrigin {

  public static final String FAMILY_ID = "SEGSENSE_DECLARED_FAMILY_CONTINUITY_V1";
  public static final String INCOME_ID = "SEGSENSE_DECLARED_INCOME_INTERRUPTION_V1";
  public static final String FIRES_ID = "SEGSENSE_DECLARED_NEARBY_FIRES_V1";
  public static final String HOME_ID = "SEGSENSE_DECLARED_HOME_PROTECTION_V1";

  private DemoDeclaredOrigin() {}

  public static String idForTheme(String theme) {
    if (DemoDeclaredContextParser.FAMILY.equals(theme)) {
      return FAMILY_ID;
    }
    if (DemoDeclaredContextParser.INCOME.equals(theme)) {
      return INCOME_ID;
    }
    if (DemoDeclaredContextParser.FIRES.equals(theme)) {
      return FIRES_ID;
    }
    if ("home_protection".equals(theme)) {
      return HOME_ID;
    }
    return null;
  }

  public static Map<String, String> attributes(String theme) {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", GovernedDemoOrigin.CHANNEL);
    attributes.put("purposeVersion", GovernedDemoOrigin.PURPOSE_VERSION);
    attributes.put("theme", theme);
    attributes.put("constraint", "no_quote");
    return attributes;
  }

  public static Map<String, Object> contribution(String theme, boolean used) {
    Map<String, Object> contribution = new LinkedHashMap<>();
    contribution.put("role", "VISITOR_DECLARED");
    contribution.put("sourceType", "USER_DECLARED");
    contribution.put("sourceId", idForTheme(theme));
    contribution.put("captureMethod", "SATELLITE_DECLARED");
    contribution.put("trustLevel", "DECLARED");
    contribution.put("used", used);
    contribution.put("elements", Map.of("theme", theme));
    return contribution;
  }

  public static Map<String, Object> governedContribution(GovernedDemoSource source, boolean used) {
    Map<String, Object> contribution = new LinkedHashMap<>();
    contribution.put("role", "GOVERNED_SOURCE");
    contribution.put("sourceType", "SATELLITE_GOVERNED");
    contribution.put("sourceId", source.id());
    contribution.put("sourceTimestamp", source.capturedAt());
    contribution.put("captureMethod", "SERVER_REGISTRY");
    contribution.put("trustLevel", "GOVERNED");
    contribution.put("used", used);
    Map<String, String> elements = new LinkedHashMap<>();
    elements.put("theme", source.theme());
    elements.put("situation", source.situation());
    elements.put("need", source.need());
    elements.put("horizon", source.horizon());
    elements.put("constraint", source.constraint());
    contribution.put("elements", elements);
    return contribution;
  }
}
