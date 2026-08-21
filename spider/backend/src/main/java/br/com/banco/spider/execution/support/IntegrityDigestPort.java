package br.com.banco.spider.execution.support;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;

public interface IntegrityDigestPort {
  String digest(String canonicalRepresentation);

  static IntegrityDigestPort sha256() {
    return canonical -> {
      try {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        byte[] hash = md.digest(canonical.getBytes(StandardCharsets.UTF_8));
        return "sha256:" + HexFormat.of().formatHex(hash);
      } catch (NoSuchAlgorithmException e) {
        throw new IllegalStateException("SHA-256 unavailable", e);
      }
    };
  }
}
