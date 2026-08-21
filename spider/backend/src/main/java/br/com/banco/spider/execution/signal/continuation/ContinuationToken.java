package br.com.banco.spider.execution.signal.continuation;

import java.security.SecureRandom;
import java.util.Arrays;
import java.util.Base64;
import java.util.Objects;

/** Bearer secret de correlação — nunca persistir/logar valor puro. */
public final class ContinuationToken {

  private static final int ENTROPY_BYTES = 32;
  private static final int MAX_WIRE_LENGTH = 64;

  private final byte[] raw;
  private final String wire;

  private ContinuationToken(byte[] raw, String wire) {
    this.raw = Objects.requireNonNull(raw);
    this.wire = Objects.requireNonNull(wire);
  }

  public static ContinuationToken generate(SecureRandom random) {
    Objects.requireNonNull(random, "random");
    byte[] bytes = new byte[ENTROPY_BYTES];
    random.nextBytes(bytes);
    String wire = Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    return new ContinuationToken(bytes, wire);
  }

  public static ContinuationToken parse(String wire) {
    if (wire == null || wire.isBlank()) {
      throw new IllegalArgumentException("TOKEN_MALFORMED");
    }
    String t = wire.trim();
    if (t.length() < 40 || t.length() > MAX_WIRE_LENGTH) {
      throw new IllegalArgumentException("TOKEN_MALFORMED");
    }
    try {
      byte[] decoded = Base64.getUrlDecoder().decode(t);
      if (decoded.length != ENTROPY_BYTES) {
        throw new IllegalArgumentException("TOKEN_MALFORMED");
      }
      return new ContinuationToken(decoded, t);
    } catch (IllegalArgumentException ex) {
      throw new IllegalArgumentException("TOKEN_MALFORMED");
    }
  }

  public String wire() {
    return wire;
  }

  public byte[] rawCopy() {
    return Arrays.copyOf(raw, raw.length);
  }

  public void zeroize() {
    Arrays.fill(raw, (byte) 0);
  }

  @Override
  public String toString() {
    return "ContinuationToken[REDACTED]";
  }

  @Override
  public boolean equals(Object o) {
    if (this == o) return true;
    if (!(o instanceof ContinuationToken that)) return false;
    return Arrays.equals(raw, that.raw);
  }

  @Override
  public int hashCode() {
    return Arrays.hashCode(raw);
  }
}
