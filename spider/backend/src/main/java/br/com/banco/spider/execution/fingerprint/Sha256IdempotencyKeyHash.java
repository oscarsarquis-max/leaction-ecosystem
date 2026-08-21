package br.com.banco.spider.execution.fingerprint;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.HexFormat;
import java.util.Objects;
import org.springframework.stereotype.Component;

/**
 * SHA-256 da chave. Limitação: sem HMAC/secret management nesta fase.
 * A chave em claro nunca é persistida.
 */
@Component
public class Sha256IdempotencyKeyHash implements IdempotencyKeyHashPort {

  @Override
  public String hash(String idempotencyKey) {
    Objects.requireNonNull(idempotencyKey, "idempotencyKey");
    String t = idempotencyKey.trim();
    if (t.isEmpty()) {
      throw new IllegalArgumentException("idempotencyKey must not be blank");
    }
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      return HexFormat.of().formatHex(md.digest(t.getBytes(StandardCharsets.UTF_8)));
    } catch (NoSuchAlgorithmException e) {
      throw new IllegalStateException(e);
    }
  }
}
