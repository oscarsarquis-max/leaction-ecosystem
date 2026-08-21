package br.com.banco.spider.security.dataprotection;

import java.util.Arrays;
import java.util.Objects;

public final class DataProtectionKeyHandle implements AutoCloseable {

  private final String keyRef;
  private final String keyVersion;
  private final DataProtectionAlgorithm algorithm;
  private final byte[] keyBytes;
  private boolean closed;

  public DataProtectionKeyHandle(
      String keyRef, String keyVersion, DataProtectionAlgorithm algorithm, byte[] keyBytes) {
    this.keyRef = Objects.requireNonNull(keyRef);
    this.keyVersion = Objects.requireNonNull(keyVersion);
    this.algorithm = Objects.requireNonNull(algorithm);
    Objects.requireNonNull(keyBytes);
    if (keyBytes.length != 32) {
      throw new IllegalArgumentException("AES-256 key must be 32 bytes");
    }
    this.keyBytes = Arrays.copyOf(keyBytes, keyBytes.length);
  }

  public String keyRef() {
    return keyRef;
  }

  public String keyVersion() {
    return keyVersion;
  }

  public DataProtectionAlgorithm algorithm() {
    return algorithm;
  }

  /** Cópia para uso imediato — caller deve zeroizar. */
  public byte[] keyMaterialCopy() {
    ensureOpen();
    return Arrays.copyOf(keyBytes, keyBytes.length);
  }

  private void ensureOpen() {
    if (closed) {
      throw new IllegalStateException("KEY_HANDLE_CLOSED");
    }
  }

  @Override
  public void close() {
    Arrays.fill(keyBytes, (byte) 0);
    closed = true;
  }

  @Override
  public String toString() {
    return "DataProtectionKeyHandle{ref=" + keyRef + ", version=" + keyVersion + "}";
  }
}
