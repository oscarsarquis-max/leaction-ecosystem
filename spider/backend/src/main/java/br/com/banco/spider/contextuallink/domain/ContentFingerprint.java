package br.com.banco.spider.contextuallink.domain;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Locale;

public final class ContentFingerprint {

  private ContentFingerprint() {}

  public static String sha256(String sourceUrl, String title, String description, String body) {
    String canonical =
        normalize(sourceUrl)
            + '\n'
            + normalize(title)
            + '\n'
            + normalize(description)
            + '\n'
            + normalize(body);
    try {
      byte[] digest =
          MessageDigest.getInstance("SHA-256").digest(canonical.getBytes(StandardCharsets.UTF_8));
      return "sha256:" + HexFormat.of().formatHex(digest);
    } catch (NoSuchAlgorithmException ex) {
      throw new IllegalStateException("SHA-256 unavailable", ex);
    }
  }

  static String normalize(String value) {
    if (value == null) {
      return "";
    }
    return value.replace('\r', ' ').replaceAll("\\s+", " ").trim().toLowerCase(Locale.ROOT);
  }
}
