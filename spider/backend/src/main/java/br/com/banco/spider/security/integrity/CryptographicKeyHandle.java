package br.com.banco.spider.security.integrity;

import java.util.Arrays;
import java.util.Objects;
import java.util.function.Function;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Handle efêmero de chave. Bytes não expostos por getter público; limpeza em close().
 * Não serializável.
 */
public final class CryptographicKeyHandle implements AutoCloseable {

  private final KeyReference reference;
  private byte[] keyBytes;
  private boolean closed;

  public CryptographicKeyHandle(KeyReference reference, byte[] keyBytes) {
    this.reference = Objects.requireNonNull(reference, "reference");
    this.keyBytes = Objects.requireNonNull(keyBytes, "keyBytes").clone();
  }

  public KeyReference reference() {
    return reference;
  }

  /** Executa MAC HmacSHA256 e limpa estado intermediário do Mac. */
  public byte[] mac(byte[] signingInput) {
    ensureOpen();
    Objects.requireNonNull(signingInput, "signingInput");
    try {
      Mac mac = Mac.getInstance("HmacSHA256");
      mac.init(new SecretKeySpec(keyBytes, "HmacSHA256"));
      return mac.doFinal(signingInput);
    } catch (Exception ex) {
      throw new CryptographicKeyException(CryptoKeyFailureCode.KEY_UNAVAILABLE);
    }
  }

  /** Acesso controlado para fingerprint — callback recebe cópia e deve limpar. */
  <T> T withKeyBytes(Function<byte[], T> consumer) {
    ensureOpen();
    byte[] copy = keyBytes.clone();
    try {
      return consumer.apply(copy);
    } finally {
      Arrays.fill(copy, (byte) 0);
    }
  }

  private void ensureOpen() {
    if (closed || keyBytes == null) {
      throw new CryptographicKeyException(CryptoKeyFailureCode.KEY_UNAVAILABLE);
    }
  }

  @Override
  public void close() {
    closed = true;
    if (keyBytes != null) {
      Arrays.fill(keyBytes, (byte) 0);
      keyBytes = null;
    }
  }

  @Override
  public String toString() {
    return "CryptographicKeyHandle{keyRef="
        + reference.keyRef()
        + ", keyVersion="
        + reference.keyVersion()
        + ", closed="
        + closed
        + "}";
  }
}
