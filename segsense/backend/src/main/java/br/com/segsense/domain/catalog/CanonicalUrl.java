package br.com.segsense.domain.catalog;

import java.net.URI;
import java.util.Locale;
import java.util.Objects;
import java.util.Optional;

public final class CanonicalUrl {

  private final String value;

  private CanonicalUrl(String value) {
    this.value = value;
  }

  public static Optional<CanonicalUrl> parseOptional(String raw) {
    if (raw == null || raw.isBlank()) {
      return Optional.empty();
    }
    return Optional.of(parse(raw));
  }

  public static CanonicalUrl parse(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new CatalogValidationException("A URL canônica informada é inválida.");
    }
    String trimmed = raw.trim();
    URI uri;
    try {
      uri = URI.create(trimmed);
    } catch (IllegalArgumentException ex) {
      throw new CatalogValidationException("A URL canônica informada é inválida.");
    }
    if (uri.getScheme() == null
        || !"https".equals(uri.getScheme().toLowerCase(Locale.ROOT))
        || !trimmed.toLowerCase(Locale.ROOT).startsWith("https://")) {
      throw new CatalogValidationException("A URL canônica deve ser HTTPS absoluta.");
    }
    if (uri.getHost() == null || uri.getHost().isBlank()) {
      throw new CatalogValidationException("A URL canônica deve ser HTTPS absoluta.");
    }
    if (uri.getUserInfo() != null) {
      throw new CatalogValidationException(
          "A URL canônica não pode conter usuário, senha ou userinfo.");
    }
    if (uri.getRawQuery() != null) {
      throw new CatalogValidationException("A URL canônica não pode conter query.");
    }
    if (uri.getRawFragment() != null) {
      throw new CatalogValidationException("A URL canônica não pode conter fragmento.");
    }
    if (trimmed.contains("@")) {
      throw new CatalogValidationException(
          "A URL canônica não pode conter usuário, senha ou userinfo.");
    }
    return new CanonicalUrl(trimmed);
  }

  public String value() {
    return value;
  }

  @Override
  public boolean equals(Object other) {
    if (this == other) {
      return true;
    }
    if (!(other instanceof CanonicalUrl that)) {
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
