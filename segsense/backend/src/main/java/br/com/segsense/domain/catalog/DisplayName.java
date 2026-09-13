package br.com.segsense.domain.catalog;

import java.util.Objects;

public final class DisplayName {

  private final String value;

  private DisplayName(String value) {
    this.value = value;
  }

  public static DisplayName parse(String raw) {
    if (raw == null) {
      throw new CatalogValidationException("O nome é obrigatório.");
    }
    String normalized = raw.trim();
    if (normalized.isEmpty()) {
      throw new CatalogValidationException("O nome é obrigatório.");
    }
    int length = normalized.length();
    if (length < 3 || length > 120) {
      throw new CatalogValidationException("O nome deve ter entre 3 e 120 caracteres.");
    }
    return new DisplayName(normalized);
  }

  public String value() {
    return value;
  }

  @Override
  public boolean equals(Object other) {
    if (this == other) {
      return true;
    }
    if (!(other instanceof DisplayName that)) {
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
