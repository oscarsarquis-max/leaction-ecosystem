package br.com.banco.spider.execution.signal.protection;

import java.time.Instant;
import java.util.Objects;

public record ProtectedSignalEnvelope(
    String protectedEnvelopeId,
    String inboxLogicalKey,
    String dataProtectionProfileRef,
    String algorithm,
    String keyRef,
    String keyVersion,
    String aadVersion,
    byte[] iv,
    byte[] ciphertextAndTag,
    String plaintextDigest,
    String ciphertextDigest,
    int plaintextSize,
    ProtectedEnvelopeState state,
    Instant createdAt,
    Instant consumedAt,
    Instant eligibleForDeletionAt,
    String leaseOwner,
    Instant leaseUntil,
    long optimisticVersion) {

  public ProtectedSignalEnvelope {
    Objects.requireNonNull(protectedEnvelopeId, "protectedEnvelopeId");
    Objects.requireNonNull(inboxLogicalKey, "inboxLogicalKey");
    Objects.requireNonNull(dataProtectionProfileRef, "dataProtectionProfileRef");
    Objects.requireNonNull(algorithm, "algorithm");
    Objects.requireNonNull(keyRef, "keyRef");
    Objects.requireNonNull(keyVersion, "keyVersion");
    Objects.requireNonNull(iv, "iv");
    Objects.requireNonNull(ciphertextAndTag, "ciphertextAndTag");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(createdAt, "createdAt");
    iv = iv.clone();
    ciphertextAndTag = ciphertextAndTag.clone();
  }

  @Override
  public String toString() {
    return "ProtectedSignalEnvelope{id="
        + protectedEnvelopeId
        + ", state="
        + state
        + ", keyVersion="
        + keyVersion
        + "}";
  }
}
