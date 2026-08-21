package br.com.banco.spider.security.integrity;

import java.time.Duration;
import java.util.List;
import java.util.Objects;

public record IntegrityProfileDefinition(
    String profileCode,
    String version,
    IntegrityPurpose purpose,
    IntegrityAlgorithm algorithm,
    String signingKeyRef,
    String activeSigningKeyVersion,
    List<String> acceptedVerificationKeyVersions,
    SigningCanonicalizationVersion canonicalizationVersion,
    Duration timestampTolerance,
    boolean nonceRequired,
    Duration replayWindow,
    int maximumPayloadDigestBytes,
    IntegrityProfileStatus status,
    String definitionIntegrityRef) {

  public IntegrityProfileDefinition {
    Objects.requireNonNull(profileCode, "profileCode");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(purpose, "purpose");
    Objects.requireNonNull(algorithm, "algorithm");
    Objects.requireNonNull(signingKeyRef, "signingKeyRef");
    Objects.requireNonNull(activeSigningKeyVersion, "activeSigningKeyVersion");
    Objects.requireNonNull(canonicalizationVersion, "canonicalizationVersion");
    Objects.requireNonNull(timestampTolerance, "timestampTolerance");
    Objects.requireNonNull(replayWindow, "replayWindow");
    Objects.requireNonNull(status, "status");
    Objects.requireNonNull(definitionIntegrityRef, "definitionIntegrityRef");
    acceptedVerificationKeyVersions =
        acceptedVerificationKeyVersions == null
            ? List.of()
            : List.copyOf(acceptedVerificationKeyVersions);
    if (algorithm != IntegrityAlgorithm.HMAC_SHA_256) {
      throw new IllegalArgumentException("Only HMAC_SHA_256 allowed in this increment");
    }
    if (replayWindow.isNegative() || replayWindow.isZero()) {
      throw new IllegalArgumentException("replayWindow must be positive");
    }
    if (replayWindow.compareTo(Duration.ofHours(24)) > 0) {
      throw new IllegalArgumentException("replayWindow exceeds conservative limit");
    }
    if (timestampTolerance.isNegative() || timestampTolerance.compareTo(replayWindow) > 0) {
      throw new IllegalArgumentException("timestampTolerance must fit within replayWindow");
    }
    if (maximumPayloadDigestBytes < 16 || maximumPayloadDigestBytes > 1_048_576) {
      throw new IllegalArgumentException("maximumPayloadDigestBytes out of bounds");
    }
    if (status == IntegrityProfileStatus.PUBLISHED) {
      if (acceptedVerificationKeyVersions.isEmpty()) {
        throw new IllegalArgumentException("PUBLISHED profile requires accepted key versions");
      }
      if (!acceptedVerificationKeyVersions.contains(activeSigningKeyVersion)) {
        throw new IllegalArgumentException("activeSigningKeyVersion must be accepted");
      }
      if (nonceRequired == false
          && (purpose == IntegrityPurpose.CALLBACK_DELIVERY
              || purpose == IntegrityPurpose.EXTERNAL_SIGNAL
              || purpose == IntegrityPurpose.CALLBACK_STATUS_QUERY)) {
        throw new IllegalArgumentException("boundary purposes require nonce");
      }
    }
  }

  public String exactRef() {
    return profileCode + "@" + version;
  }

  public boolean canSign() {
    return status == IntegrityProfileStatus.PUBLISHED;
  }

  public boolean canVerifyWithKeyVersion(String keyVersion) {
    if (status == IntegrityProfileStatus.REVOKED || status == IntegrityProfileStatus.RETIRED) {
      return false;
    }
    return keyVersion != null && acceptedVerificationKeyVersions.contains(keyVersion);
  }

  public static IntegrityProfileDefinition publishedHmac(
      String code,
      String version,
      IntegrityPurpose purpose,
      String keyRef,
      String activeVersion,
      List<String> acceptedVersions,
      Duration replayWindow) {
    return new IntegrityProfileDefinition(
        code,
        version,
        purpose,
        IntegrityAlgorithm.HMAC_SHA_256,
        keyRef,
        activeVersion,
        acceptedVersions,
        SigningCanonicalizationVersion.SPIDER_SIGNING_INPUT_V1,
        Duration.ofMinutes(1),
        true,
        replayWindow,
        65536,
        IntegrityProfileStatus.PUBLISHED,
        "integrity:profile:" + code + "@" + version);
  }
}
