package br.com.segsense.domain.catalog;

import java.util.Locale;
import java.util.Objects;
import java.util.regex.Pattern;

public final class ResourceKey {

  private static final Pattern PATTERN = Pattern.compile("^[a-z][a-z0-9-]{2,49}$");

  private final String value;

  private ResourceKey(String value) {
    this.value = value;
  }

  public static ResourceKey parse(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("A chave é obrigatória.");
    }
    String normalized = raw.trim().toLowerCase(Locale.ROOT);
    if (!PATTERN.matcher(normalized).matches()) {
      throw new CatalogValidationException(
          "A chave deve ter de 3 a 50 caracteres, começar com letra e conter apenas minúsculas, números ou hífen.");
    }
    return new ResourceKey(normalized);
  }

  public static ResourceKey restored(String stored) {
    return parse(stored);
  }

  public String value() {
    return value;
  }

  @Override
  public boolean equals(Object other) {
    if (this == other) {
      return true;
    }
    if (!(other instanceof ResourceKey that)) {
      return false;
    }
    return value.equals(that.value);
  }

  @Override
  public int hashCode() {
    return Objects.hash(value);
  }

  @Override
  public String toString() {
    return value;
  }
}
