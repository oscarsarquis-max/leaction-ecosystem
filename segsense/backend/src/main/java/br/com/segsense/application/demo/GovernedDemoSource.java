package br.com.segsense.application.demo;

import java.util.LinkedHashMap;
import java.util.Map;

public record GovernedDemoSource(
    String id,
    String slug,
    String title,
    String sourceLabel,
    String version,
    String capturedAt,
    String theme,
    String situation,
    String need,
    String horizon,
    String constraint,
    String authorizedExcerpt,
    boolean revoked) {

  public Map<String, String> attributes() {
    Map<String, String> attributes = new LinkedHashMap<>();
    attributes.put("channel", GovernedDemoOrigin.CHANNEL);
    attributes.put("editorialPieceVersion", version);
    attributes.put("purposeVersion", GovernedDemoOrigin.PURPOSE_VERSION);
    attributes.put("theme", theme);
    attributes.put("situation", situation);
    attributes.put("need", need);
    attributes.put("horizon", horizon);
    attributes.put("constraint", constraint);
    return attributes;
  }
}
