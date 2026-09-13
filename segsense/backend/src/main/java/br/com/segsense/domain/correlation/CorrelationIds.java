package br.com.segsense.domain.correlation;

import java.util.Optional;
import java.util.UUID;

public final class CorrelationIds {

  private CorrelationIds() {}

  public static Optional<UUID> parseValid(String raw) {
    if (raw == null || raw.isBlank()) {
      return Optional.empty();
    }
    try {
      return Optional.of(UUID.fromString(raw.trim()));
    } catch (IllegalArgumentException ignored) {
      return Optional.empty();
    }
  }

  public static UUID resolve(String raw) {
    return parseValid(raw).orElseGet(UUID::randomUUID);
  }
}
