package br.com.segsense.domain.link;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;
import java.util.Objects;
import java.util.regex.Pattern;

public final class OpaqueToken {

  public static final int RAW_BYTE_LENGTH = 32;
  public static final int ENCODED_LENGTH = 43;
  private static final Pattern ENCODED = Pattern.compile("^[A-Za-z0-9_-]{43}$");

  private OpaqueToken() {}

  public static boolean isWellFormed(String raw) {
    return raw != null && ENCODED.matcher(raw).matches();
  }

  public static byte[] digest(String rawToken) {
    if (!isWellFormed(rawToken)) {
      throw new IllegalArgumentException("token");
    }
    try {
      return MessageDigest.getInstance("SHA-256")
          .digest(rawToken.getBytes(StandardCharsets.US_ASCII));
    } catch (NoSuchAlgorithmException exception) {
      throw new IllegalStateException("SHA-256 required", exception);
    }
  }

  public static String hint(String rawToken) {
    if (!isWellFormed(rawToken)) {
      throw new IllegalArgumentException("token");
    }
    return rawToken.substring(0, 8);
  }

  public static byte[] requireDigest(byte[] digest) {
    Objects.requireNonNull(digest, "digest");
    if (digest.length != RAW_BYTE_LENGTH) {
      throw new IllegalArgumentException("digest");
    }
    return Arrays.copyOf(digest, digest.length);
  }
}
