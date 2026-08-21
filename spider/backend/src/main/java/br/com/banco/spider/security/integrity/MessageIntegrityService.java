package br.com.banco.spider.security.integrity;

import br.com.banco.spider.execution.support.SpiderClock;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.HexFormat;
import java.util.Objects;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/** Serviço de MAC — bean criado por IntegritySecurityConfig quando integrity habilitada. */
public class MessageIntegrityService {

  private static final Logger log = LoggerFactory.getLogger(MessageIntegrityService.class);

  private final CryptographicKeyMaterialProviderPort keyProvider;
  private final IntegrityProfileCatalogPort profileCatalog;
  private final IntegrityKeyRotationService rotationService;
  private final SpiderClock clock;
  private final SecureRandom secureRandom = new SecureRandom();

  public MessageIntegrityService(
      CryptographicKeyMaterialProviderPort keyProvider,
      IntegrityProfileCatalogPort profileCatalog,
      IntegrityKeyRotationService rotationService,
      SpiderClock clock) {
    this.keyProvider = keyProvider;
    this.profileCatalog = profileCatalog;
    this.rotationService = rotationService;
    this.clock = clock;
  }

  public String newNonce() {
    byte[] n = new byte[16];
    secureRandom.nextBytes(n);
    return Base64.getUrlEncoder().withoutPadding().encodeToString(n);
  }

  public Mono<IntegrityProof> sign(
      SigningMaterial baseMaterialWithoutKeyVersion, IntegrityProfileDefinition profile) {
    Objects.requireNonNull(baseMaterialWithoutKeyVersion, "material");
    Objects.requireNonNull(profile, "profile");
    if (!profile.canSign()) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.KEY_VERSION_NOT_ALLOWED));
    }
    String keyVersion = rotationService.activeSigningVersion(profile);
    KeyReference keyRef =
        new KeyReference(
            profile.signingKeyRef(), keyVersion, profile.purpose(), profile.algorithm());
    SigningMaterial material =
        new SigningMaterial(
            baseMaterialWithoutKeyVersion.domainSeparator(),
            profile.exactRef(),
            profile.algorithm(),
            profile.signingKeyRef(),
            keyVersion,
            baseMaterialWithoutKeyVersion.contractRef(),
            baseMaterialWithoutKeyVersion.messageType(),
            baseMaterialWithoutKeyVersion.executionOrCorrelationId(),
            baseMaterialWithoutKeyVersion.deliveryOrMessageId(),
            baseMaterialWithoutKeyVersion.attemptNumber(),
            baseMaterialWithoutKeyVersion.issuedAt(),
            baseMaterialWithoutKeyVersion.expiresAt(),
            baseMaterialWithoutKeyVersion.nonce(),
            baseMaterialWithoutKeyVersion.payloadDigestAlgorithm(),
            baseMaterialWithoutKeyVersion.payloadDigest(),
            profile.canonicalizationVersion());
    if (profile.nonceRequired() && (material.nonce() == null || material.nonce().isBlank())) {
      return Mono.error(new IllegalStateException("NONCE_MISSING"));
    }
    byte[] input = SigningInputCanonicalizerV1.canonicalize(material);
    return keyProvider
        .resolveForSigning(keyRef)
        .map(
            handle -> {
              try (handle) {
                byte[] mac = handle.mac(input);
                log.info(
                    "event=integrity_sign_success purpose={} profileRef={} keyVersion={}",
                    profile.purpose(),
                    profile.exactRef(),
                    keyVersion);
                return new IntegrityProof(
                    profile.exactRef(),
                    profile.algorithm(),
                    profile.signingKeyRef(),
                    keyVersion,
                    profile.canonicalizationVersion(),
                    material.issuedAt(),
                    material.expiresAt(),
                    material.nonce(),
                    material.payloadDigestAlgorithm(),
                    material.payloadDigest(),
                    IntegrityProof.encodeMac(mac));
              }
            })
        .doOnError(
            ex ->
                log.info(
                    "event=integrity_sign_failure purpose={} reasonCode={}",
                    profile.purpose(),
                    ex instanceof CryptographicKeyException cke
                        ? cke.code().name()
                        : "CRYPTOGRAPHIC_OPERATION_FAILED"));
  }

  public Mono<IntegrityVerificationResult> verify(
      SigningMaterial materialFromProofFields, IntegrityProof proof) {
    Objects.requireNonNull(proof, "proof");
    Instant now = clock.now();
    if (proof.nonce() == null || proof.nonce().isBlank()) {
      return Mono.just(
          new IntegrityVerificationResult(IntegrityVerificationDisposition.NONCE_MISSING));
    }
    if (proof.issuedAt().isAfter(now.plus(Duration.ofSeconds(5)))) {
      return Mono.just(
          new IntegrityVerificationResult(IntegrityVerificationDisposition.ISSUED_IN_FUTURE));
    }
    if (!proof.expiresAt().isAfter(now)) {
      return Mono.just(new IntegrityVerificationResult(IntegrityVerificationDisposition.EXPIRED));
    }
    IntegrityProfileDefinition profile =
        profileCatalog.findByExactRef(proof.profileRef()).orElse(null);
    if (profile == null || !rotationService.isVerificationAllowed(profile, proof.keyVersion())) {
      return Mono.just(
          new IntegrityVerificationResult(
              profile == null
                  ? IntegrityVerificationDisposition.PROFILE_NOT_ALLOWED
                  : IntegrityVerificationDisposition.KEY_VERSION_NOT_ALLOWED));
    }
    if (proof.algorithm() != profile.algorithm()) {
      return Mono.just(
          new IntegrityVerificationResult(IntegrityVerificationDisposition.MALFORMED_PROOF));
    }
    byte[] expectedMac;
    try {
      expectedMac = IntegrityProof.decodeMacStrict(proof.mac(), 64);
    } catch (IllegalArgumentException ex) {
      return Mono.just(
          new IntegrityVerificationResult(IntegrityVerificationDisposition.MALFORMED_PROOF));
    }
    SigningMaterial material =
        new SigningMaterial(
            materialFromProofFields.domainSeparator(),
            proof.profileRef(),
            proof.algorithm(),
            proof.keyRef(),
            proof.keyVersion(),
            materialFromProofFields.contractRef(),
            materialFromProofFields.messageType(),
            materialFromProofFields.executionOrCorrelationId(),
            materialFromProofFields.deliveryOrMessageId(),
            materialFromProofFields.attemptNumber(),
            proof.issuedAt(),
            proof.expiresAt(),
            proof.nonce(),
            proof.payloadDigestAlgorithm(),
            proof.payloadDigest(),
            proof.canonicalizationVersion());
    if (!Objects.equals(
        materialFromProofFields.payloadDigest(), proof.payloadDigest())) {
      return Mono.just(
          new IntegrityVerificationResult(
              IntegrityVerificationDisposition.PAYLOAD_DIGEST_MISMATCH));
    }
    byte[] input = SigningInputCanonicalizerV1.canonicalize(material);
    KeyReference keyRef =
        new KeyReference(proof.keyRef(), proof.keyVersion(), profile.purpose(), proof.algorithm());
    return keyProvider
        .resolveForVerification(keyRef)
        .map(
            handle -> {
              try (handle) {
                byte[] actual = handle.mac(input);
                boolean ok = MessageDigest.isEqual(actual, expectedMac);
                log.info(
                    "event=integrity_verify_{} purpose={} keyVersion={}",
                    ok ? "success" : "failure",
                    profile.purpose(),
                    proof.keyVersion());
                return new IntegrityVerificationResult(
                    ok
                        ? IntegrityVerificationDisposition.VERIFIED
                        : IntegrityVerificationDisposition.INVALID_MAC);
              }
            })
        .onErrorResume(
            CryptographicKeyException.class,
            ex -> {
              IntegrityVerificationDisposition d =
                  switch (ex.code()) {
                    case KEY_UNAVAILABLE -> IntegrityVerificationDisposition.KEY_UNAVAILABLE;
                    case KEY_REVOKED, KEY_VERSION_NOT_ALLOWED ->
                        IntegrityVerificationDisposition.KEY_VERSION_NOT_ALLOWED;
                    default -> IntegrityVerificationDisposition.KEY_UNAVAILABLE;
                  };
              return Mono.just(new IntegrityVerificationResult(d));
            });
  }

  /** Helper para testes golden — MAC hex de input bytes com handle. */
  public static String macHex(CryptographicKeyHandle handle, byte[] input) {
    return HexFormat.of().formatHex(handle.mac(input));
  }
}
