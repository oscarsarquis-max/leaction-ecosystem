package br.com.segsense.domain.consent;

import java.util.regex.Pattern;

public final class IdempotencyKey {

  private static final int MIN_LENGTH = 16;
  private static final int MAX_LENGTH = 128;
  private static final Pattern ALLOWED = Pattern.compile("[A-Za-z0-9._~-]{16,128}");

  private IdempotencyKey() {}

  public static String required(String raw) {
    if (raw == null || raw.isBlank()) {
      throw new IdempotencyKeyRequiredException();
    }
    String value = raw.trim();
    if (value.length() < MIN_LENGTH
        || value.length() > MAX_LENGTH
        || !ALLOWED.matcher(value).matches()
        || value.chars().distinct().count() < 8) {
      throw new InvalidIdempotencyKeyException();
    }
    return value;
  }
}
