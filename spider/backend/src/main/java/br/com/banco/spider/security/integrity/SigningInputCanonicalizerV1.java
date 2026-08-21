package br.com.banco.spider.security.integrity;

import java.nio.ByteBuffer;
import java.nio.charset.StandardCharsets;
import java.time.Instant;
import java.util.Objects;

/**
 * Canonicalização determinística SPIDER_SIGNING_INPUT_V1.
 * Campos length-prefixed UTF-8; null ≠ empty ≠ absent (absent = sentinel -1).
 */
public final class SigningInputCanonicalizerV1 {

  public static final String DOMAIN_CALLBACK_DELIVERY = "SPIDER/CALLBACK_DELIVERY/V1";
  public static final String DOMAIN_STATUS_QUERY = "SPIDER/CALLBACK_STATUS_QUERY/V1";
  public static final String DOMAIN_EXTERNAL_SIGNAL = "SPIDER/EXTERNAL_SIGNAL/V1";
  public static final String DOMAIN_SENSITIVE_FINGERPRINT = "SPIDER/SENSITIVE_FINGERPRINT/V1";

  private SigningInputCanonicalizerV1() {}

  public static byte[] canonicalize(SigningMaterial material) {
    Objects.requireNonNull(material, "material");
    ByteBuffer buf = ByteBuffer.allocate(estimate(material));
    writeString(buf, material.domainSeparator());
    writeString(buf, material.profileRef());
    writeString(buf, material.algorithm().name());
    writeString(buf, material.keyRef());
    writeString(buf, material.keyVersion());
    writeString(buf, material.contractRef());
    writeString(buf, material.messageType());
    writeString(buf, material.executionOrCorrelationId());
    writeString(buf, material.deliveryOrMessageId());
    writeInt(buf, material.attemptNumber());
    writeInstant(buf, material.issuedAt());
    writeInstant(buf, material.expiresAt());
    writeString(buf, material.nonce());
    writeString(buf, material.payloadDigestAlgorithm());
    writeString(buf, material.payloadDigest());
    writeString(buf, material.canonicalizationVersion().name());
    buf.flip();
    byte[] out = new byte[buf.remaining()];
    buf.get(out);
    return out;
  }

  private static int estimate(SigningMaterial m) {
    return 512
        + len(m.domainSeparator())
        + len(m.profileRef())
        + len(m.keyRef())
        + len(m.nonce())
        + len(m.payloadDigest())
        + 64;
  }

  private static int len(String s) {
    return s == null ? 4 : 4 + s.getBytes(StandardCharsets.UTF_8).length;
  }

  /** null → length -1; empty → length 0; present → length + UTF-8 bytes */
  static void writeString(ByteBuffer buf, String value) {
    if (value == null) {
      buf.putInt(-1);
      return;
    }
    byte[] bytes = value.getBytes(StandardCharsets.UTF_8);
    buf.putInt(bytes.length);
    buf.put(bytes);
  }

  static void writeInt(ByteBuffer buf, int value) {
    buf.putInt(value);
  }

  /** Instant as epoch millis UTC; null → Long.MIN_VALUE sentinel */
  static void writeInstant(ByteBuffer buf, Instant value) {
    if (value == null) {
      buf.putLong(Long.MIN_VALUE);
    } else {
      buf.putLong(value.toEpochMilli());
    }
  }
}
