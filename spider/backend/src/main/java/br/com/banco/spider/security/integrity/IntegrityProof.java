package br.com.banco.spider.security.integrity;

import java.time.Instant;
import java.util.Base64;
import java.util.Objects;

public record IntegrityProof(
    String profileRef,
    IntegrityAlgorithm algorithm,
    String keyRef,
    String keyVersion,
    SigningCanonicalizationVersion canonicalizationVersion,
    Instant issuedAt,
    Instant expiresAt,
    String nonce,
    String payloadDigestAlgorithm,
    String payloadDigest,
    String mac) {

  public IntegrityProof {
    Objects.requireNonNull(profileRef, "profileRef");
    Objects.requireNonNull(algorithm, "algorithm");
    Objects.requireNonNull(keyRef, "keyRef");
    Objects.requireNonNull(keyVersion, "keyVersion");
    Objects.requireNonNull(canonicalizationVersion, "canonicalizationVersion");
    Objects.requireNonNull(issuedAt, "issuedAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
    Objects.requireNonNull(payloadDigestAlgorithm, "payloadDigestAlgorithm");
    Objects.requireNonNull(payloadDigest, "payloadDigest");
    Objects.requireNonNull(mac, "mac");
  }

  public String macFingerprintShort() {
    if (mac.length() < 8) {
      return "****";
    }
    return mac.substring(mac.length() - 8);
  }

  public static String encodeMac(byte[] macBytes) {
    return Base64.getUrlEncoder().withoutPadding().encodeToString(macBytes);
  }

  public static byte[] decodeMacStrict(String mac, int maxBytes) {
    if (mac == null || mac.isBlank()) {
      throw new IllegalArgumentException("MALFORMED_PROOF");
    }
    byte[] decoded;
    try {
      decoded = Base64.getUrlDecoder().decode(mac);
    } catch (IllegalArgumentException ex) {
      throw new IllegalArgumentException("MALFORMED_PROOF");
    }
    if (decoded.length == 0 || decoded.length > maxBytes) {
      throw new IllegalArgumentException("MALFORMED_PROOF");
    }
    return decoded;
  }

  @Override
  public String toString() {
    return "IntegrityProof{profileRef="
        + profileRef
        + ", algorithm="
        + algorithm
        + ", keyRef="
        + keyRef
        + ", keyVersion="
        + keyVersion
        + ", mac=****"
        + macFingerprintShort()
        + ", nonce=****, digest=****}";
  }
}
