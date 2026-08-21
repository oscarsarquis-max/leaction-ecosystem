package br.com.banco.spider.security.integrity;

import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import java.util.Base64;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;

/**
 * Fingerprint sensível. Default: SHA-256 v1 (compat). HMAC v2 somente quando habilitado + provider.
 */
@Service
public class SensitiveFingerprintService {

  private static final Logger log = LoggerFactory.getLogger(SensitiveFingerprintService.class);

  private final ObjectProvider<CryptographicKeyMaterialProviderPort> keyProvider;
  private final IntegrityProfileCatalogPort profileCatalog;
  private final Sha256IdempotencyKeyHash sha256;
  private final boolean v2Enabled;

  public SensitiveFingerprintService(
      ObjectProvider<CryptographicKeyMaterialProviderPort> keyProvider,
      IntegrityProfileCatalogPort profileCatalog,
      Sha256IdempotencyKeyHash sha256,
      @Value("${spider.security.sensitive-fingerprint-v2.enabled:false}") boolean v2Enabled) {
    this.keyProvider = keyProvider;
    this.profileCatalog = profileCatalog;
    this.sha256 = sha256;
    this.v2Enabled = v2Enabled;
  }

  public VersionedFingerprint fingerprintV1(String value) {
    return new VersionedFingerprint(
        FingerprintAlgorithmVersion.V1_SHA256, null, null, sha256.hash(value));
  }

  public Mono<VersionedFingerprint> fingerprint(String scope, String value, String profileRef) {
    Objects.requireNonNull(scope, "scope");
    Objects.requireNonNull(value, "value");
    CryptographicKeyMaterialProviderPort provider = keyProvider.getIfAvailable();
    if (!v2Enabled || provider == null) {
      log.info("event=legacy_fingerprint_v1_lookup scopeBucket={}", scopeBucket(scope));
      return Mono.just(fingerprintV1(value));
    }
    IntegrityProfileDefinition profile =
        profileCatalog
            .findPublished(profileRef, IntegrityPurpose.SENSITIVE_FINGERPRINT)
            .orElse(null);
    if (profile == null) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.KEY_NOT_FOUND));
    }
    KeyReference ref =
        new KeyReference(
            profile.signingKeyRef(),
            profile.activeSigningKeyVersion(),
            IntegrityPurpose.SENSITIVE_FINGERPRINT,
            profile.algorithm());
    byte[] input =
        SigningInputCanonicalizerV1.canonicalize(
            new SigningMaterial(
                SigningInputCanonicalizerV1.DOMAIN_SENSITIVE_FINGERPRINT,
                profile.exactRef(),
                profile.algorithm(),
                profile.signingKeyRef(),
                profile.activeSigningKeyVersion(),
                scope,
                "FINGERPRINT",
                null,
                value,
                0,
                java.time.Instant.EPOCH,
                java.time.Instant.EPOCH.plusSeconds(1),
                "",
                CanonicalPayloadDigestService.ALGORITHM,
                sha256.hash(value),
                SigningCanonicalizationVersion.SPIDER_SIGNING_INPUT_V1));
    return provider
        .resolveForSigning(ref)
        .map(
            handle -> {
              try (handle) {
                String dig =
                    Base64.getUrlEncoder().withoutPadding().encodeToString(handle.mac(input));
                log.info(
                    "event=fingerprint_v2_creation scopeBucket={} keyVersion={}",
                    scopeBucket(scope),
                    profile.activeSigningKeyVersion());
                return new VersionedFingerprint(
                    FingerprintAlgorithmVersion.V2_HMAC_SHA256,
                    profile.signingKeyRef(),
                    profile.activeSigningKeyVersion(),
                    dig);
              }
            });
  }

  public boolean matchesLegacyOrVersioned(String storedDigest, String clearValue) {
    if (storedDigest == null) {
      return false;
    }
    String v1 = sha256.hash(clearValue);
    if (storedDigest.equals(v1) || storedDigest.equals("v1:" + v1)) {
      log.info("event=legacy_fingerprint_v1_reuse reasonCode=MATCH");
      return true;
    }
    return false;
  }

  private static String scopeBucket(String scope) {
    return scope == null ? "unknown" : scope.replaceAll("[^a-zA-Z0-9_-]", "_");
  }
}
