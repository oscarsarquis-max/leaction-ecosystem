package br.com.banco.spider.security.dataprotection;

import br.com.banco.spider.governance.GovernanceLifecycleState;
import java.util.List;
import java.util.Objects;

/**
 * Artifact governado — sem key material. Purpose fechado EXTERNAL_SIGNAL_ENVELOPE_AT_REST.
 */
public record DataProtectionProfileDefinition(
    String profileCode,
    String version,
    DataProtectionPurpose purpose,
    DataProtectionAlgorithm algorithm,
    String keyRef,
    String activeEncryptionKeyVersion,
    List<String> acceptedDecryptionKeyVersions,
    String aadVersion,
    List<String> envelopeCodecVersions,
    int maximumPlaintextBytes,
    String retentionPolicyRef,
    GovernanceLifecycleState status,
    String definitionIntegrityRef) {

  public DataProtectionProfileDefinition {
    profileCode = Objects.requireNonNull(profileCode, "profileCode").trim();
    version = Objects.requireNonNull(version, "version").trim();
    Objects.requireNonNull(purpose, "purpose");
    Objects.requireNonNull(algorithm, "algorithm");
    keyRef = Objects.requireNonNull(keyRef, "keyRef").trim();
    activeEncryptionKeyVersion =
        Objects.requireNonNull(activeEncryptionKeyVersion, "activeEncryptionKeyVersion").trim();
    acceptedDecryptionKeyVersions =
        acceptedDecryptionKeyVersions == null
            ? List.of(activeEncryptionKeyVersion)
            : List.copyOf(acceptedDecryptionKeyVersions);
    aadVersion =
        aadVersion == null || aadVersion.isBlank() ? "V1" : aadVersion.trim();
    envelopeCodecVersions =
        envelopeCodecVersions == null || envelopeCodecVersions.isEmpty()
            ? List.of("VERIFIED_SIGNAL_ENVELOPE_V1")
            : List.copyOf(envelopeCodecVersions);
    Objects.requireNonNull(status, "status");
    if (purpose != DataProtectionPurpose.EXTERNAL_SIGNAL_ENVELOPE_AT_REST) {
      throw new IllegalArgumentException("unsupported purpose");
    }
    if (algorithm != DataProtectionAlgorithm.AES_256_GCM) {
      throw new IllegalArgumentException("unsupported algorithm");
    }
    if (maximumPlaintextBytes <= 0 || maximumPlaintextBytes > 262_144) {
      throw new IllegalArgumentException("maximumPlaintextBytes out of range");
    }
    retentionPolicyRef =
        retentionPolicyRef == null || retentionPolicyRef.isBlank()
            ? "retention:signal-envelope:default@1.0"
            : retentionPolicyRef.trim();
    definitionIntegrityRef =
        definitionIntegrityRef == null || definitionIntegrityRef.isBlank()
            ? null
            : definitionIntegrityRef.trim();
  }

  /** Compat com callers que usavam activeKeyVersion. */
  public String activeKeyVersion() {
    return activeEncryptionKeyVersion;
  }

  public String exactRef() {
    return "dp:" + profileCode + "@" + version;
  }

  public boolean isEligibleForEncrypt() {
    return status == GovernanceLifecycleState.PUBLISHED;
  }

  public boolean canDecryptWith(String keyVersion) {
    return keyVersion != null && acceptedDecryptionKeyVersions.contains(keyVersion);
  }

  public static DataProtectionProfileDefinition publishedAes256(
      String code, String version, String keyRef, String keyVersion) {
    return new DataProtectionProfileDefinition(
        code,
        version,
        DataProtectionPurpose.EXTERNAL_SIGNAL_ENVELOPE_AT_REST,
        DataProtectionAlgorithm.AES_256_GCM,
        keyRef,
        keyVersion,
        List.of(keyVersion),
        "V1",
        List.of("VERIFIED_SIGNAL_ENVELOPE_V1"),
        262_144,
        "retention:signal-envelope:default@1.0",
        GovernanceLifecycleState.PUBLISHED,
        null);
  }
}
