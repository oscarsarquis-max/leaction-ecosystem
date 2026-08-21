package br.com.banco.spider.security.integrity;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Base64;
import java.util.Objects;
import org.springframework.stereotype.Service;

/** Digest de conteúdo canônico (SHA-256) — não prova autenticidade. */
@Service
public class CanonicalPayloadDigestService {

  public static final String ALGORITHM = "SHA-256";

  public String digestUtf8(String canonicalProjection, int maxBytes) {
    Objects.requireNonNull(canonicalProjection, "canonicalProjection");
    byte[] bytes = canonicalProjection.getBytes(StandardCharsets.UTF_8);
    if (bytes.length > maxBytes) {
      throw new IllegalArgumentException("PAYLOAD_TOO_LARGE");
    }
    return digestBytes(bytes);
  }

  public String digestBytes(byte[] payloadBytes) {
    Objects.requireNonNull(payloadBytes, "payloadBytes");
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] dig = md.digest(payloadBytes);
      return Base64.getUrlEncoder().withoutPadding().encodeToString(dig);
    } catch (Exception ex) {
      throw new IllegalStateException("CRYPTOGRAPHIC_OPERATION_FAILED");
    }
  }

  public boolean secureEquals(String a, String b) {
    if (a == null || b == null) {
      return false;
    }
    byte[] x = a.getBytes(StandardCharsets.UTF_8);
    byte[] y = b.getBytes(StandardCharsets.UTF_8);
    return MessageDigest.isEqual(x, y);
  }
}
