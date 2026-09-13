package br.com.segsense.domain.identity;

final class IdentityValues {

  private IdentityValues() {}

  static String requireNormalized(String raw, String fieldName) {
    if (raw == null || raw.isBlank()) {
      throw new IllegalArgumentException(fieldName + " must not be blank");
    }
    String normalized = raw.trim();
    if (normalized.isEmpty()) {
      throw new IllegalArgumentException(fieldName + " must not be blank");
    }
    return normalized;
  }
}
