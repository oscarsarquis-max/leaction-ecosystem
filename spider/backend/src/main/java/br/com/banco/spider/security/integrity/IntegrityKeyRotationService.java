package br.com.banco.spider.security.integrity;

import org.springframework.stereotype.Component;

public class IntegrityKeyRotationService {

  public String activeSigningVersion(IntegrityProfileDefinition profile) {
    if (!profile.canSign()) {
      throw new CryptographicKeyException(CryptoKeyFailureCode.KEY_VERSION_NOT_ALLOWED);
    }
    return profile.activeSigningKeyVersion();
  }

  public boolean isVerificationAllowed(IntegrityProfileDefinition profile, String keyVersion) {
    return profile.canVerifyWithKeyVersion(keyVersion);
  }

  public void rejectDowngrade(String fixedVersion, String requestedVersion) {
    if (fixedVersion != null
        && requestedVersion != null
        && !fixedVersion.equals(requestedVersion)
        && compareVersionLabel(requestedVersion, fixedVersion) < 0) {
      throw new CryptographicKeyException(CryptoKeyFailureCode.KEY_VERSION_NOT_ALLOWED);
    }
  }

  /** Comparação lexicográfica simples de labels tipo v1/v2. */
  static int compareVersionLabel(String a, String b) {
    return a.compareTo(b);
  }

  public record KeyVersionSummary(String profileRef, String activeVersion, int acceptedCount) {}

  public KeyVersionSummary summarize(IntegrityProfileDefinition profile) {
    return new KeyVersionSummary(
        profile.exactRef(),
        profile.activeSigningKeyVersion(),
        profile.acceptedVerificationKeyVersions().size());
  }
}
