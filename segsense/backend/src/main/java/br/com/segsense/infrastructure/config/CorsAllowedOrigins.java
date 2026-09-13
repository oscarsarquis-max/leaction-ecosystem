package br.com.segsense.infrastructure.config;

import java.util.Arrays;

public final class CorsAllowedOrigins {

  private CorsAllowedOrigins() {}

  public static String[] parse(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new IllegalArgumentException("CORS origin list is required");
    }
    String[] origins =
        Arrays.stream(raw.split(","))
            .map(String::trim)
            .filter(part -> !part.isEmpty())
            .toArray(String[]::new);
    if (origins.length == 0) {
      throw new IllegalArgumentException("CORS origin list is empty");
    }
    for (String origin : origins) {
      if ("*".equals(origin) || origin.contains("*")) {
        throw new IllegalArgumentException("CORS wildcard is not allowed");
      }
    }
    return origins;
  }

  public static boolean allows(String[] origins, String origin) {
    if (origin == null) {
      return false;
    }
    for (String allowed : origins) {
      if (allowed.equals(origin)) {
        return true;
      }
    }
    return false;
  }
}
