package br.com.banco.spider.security.integrity;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.security.integrity.mock.MockCryptographicKeyMaterialProvider;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class IntegrityHmacCoreTest {

  private static final Instant NOW = Instant.parse("2026-08-21T18:00:00Z");

  private IntegrityProfileDefinition profile;
  private MessageIntegrityService integrity;
  private MockCryptographicKeyMaterialProvider keys;

  @BeforeEach
  void setUp() {
    profile =
        IntegrityProfileDefinition.publishedHmac(
            "integrity:callback",
            "1.0",
            IntegrityPurpose.CALLBACK_DELIVERY,
            "key:test-callback",
            "v1",
            List.of("v1", "v2"),
            Duration.ofMinutes(5));
    keys = new MockCryptographicKeyMaterialProvider();
    integrity =
        new MessageIntegrityService(
            keys,
            new ConfiguredIntegrityProfileCatalog(List.of(profile)),
            new IntegrityKeyRotationService(),
            SpiderClock.fixed(NOW));
  }

  @Test
  void goldenVectorSigningInputV1IsStable() {
    SigningMaterial material = sampleMaterial("nonce-1", "digest-abc");
    byte[] a = SigningInputCanonicalizerV1.canonicalize(material);
    byte[] b = SigningInputCanonicalizerV1.canonicalize(material);
    assertArrayEquals(a, b);
    // frozen length prefix structure — first domain separator length
    assertEquals(SigningInputCanonicalizerV1.DOMAIN_CALLBACK_DELIVERY.length(), 
        ((a[0] & 0xff) << 24) | ((a[1] & 0xff) << 16) | ((a[2] & 0xff) << 8) | (a[3] & 0xff));
  }

  @Test
  void fieldChangeAltersCanonicalBytes() {
    byte[] base = SigningInputCanonicalizerV1.canonicalize(sampleMaterial("n1", "d1"));
    byte[] changed =
        SigningInputCanonicalizerV1.canonicalize(sampleMaterial("n2", "d1"));
    assertFalse(java.util.Arrays.equals(base, changed));
  }

  @Test
  void nullEmptyDistinct() {
    SigningMaterial withNull =
        new SigningMaterial(
            SigningInputCanonicalizerV1.DOMAIN_CALLBACK_DELIVERY,
            profile.exactRef(),
            IntegrityAlgorithm.HMAC_SHA_256,
            "key:test-callback",
            "v1",
            null,
            "CALLBACK_DELIVERY",
            "e1",
            "cb1",
            1,
            NOW,
            NOW.plusSeconds(60),
            "n",
            "SHA-256",
            "d",
            SigningCanonicalizationVersion.SPIDER_SIGNING_INPUT_V1);
    SigningMaterial withEmpty =
        new SigningMaterial(
            SigningInputCanonicalizerV1.DOMAIN_CALLBACK_DELIVERY,
            profile.exactRef(),
            IntegrityAlgorithm.HMAC_SHA_256,
            "key:test-callback",
            "v1",
            "",
            "CALLBACK_DELIVERY",
            "e1",
            "cb1",
            1,
            NOW,
            NOW.plusSeconds(60),
            "n",
            "SHA-256",
            "d",
            SigningCanonicalizationVersion.SPIDER_SIGNING_INPUT_V1);
    assertFalse(
        java.util.Arrays.equals(
            SigningInputCanonicalizerV1.canonicalize(withNull),
            SigningInputCanonicalizerV1.canonicalize(withEmpty)));
  }

  @Test
  void domainSeparatorsIsolateProofs() {
    SigningMaterial cb = sampleMaterial("n", "d");
    SigningMaterial sig =
        new SigningMaterial(
            SigningInputCanonicalizerV1.DOMAIN_EXTERNAL_SIGNAL,
            profile.exactRef(),
            IntegrityAlgorithm.HMAC_SHA_256,
            "key:test-callback",
            "v1",
            "contract",
            "CALLBACK_DELIVERY",
            "e1",
            "cb1",
            1,
            NOW,
            NOW.plusSeconds(60),
            "n",
            "SHA-256",
            "d",
            SigningCanonicalizationVersion.SPIDER_SIGNING_INPUT_V1);
    assertFalse(
        java.util.Arrays.equals(
            SigningInputCanonicalizerV1.canonicalize(cb),
            SigningInputCanonicalizerV1.canonicalize(sig)));
  }

  @Test
  void signAndVerifyRoundTrip() {
    SigningMaterial material = sampleMaterial(integrity.newNonce(), "payload-digest-1");
    StepVerifier.create(integrity.sign(material, profile))
        .assertNext(
            proof -> {
              assertEquals("v1", proof.keyVersion());
              assertFalse(proof.toString().contains(proof.mac()));
              StepVerifier.create(integrity.verify(material, proof))
                  .assertNext(r -> assertTrue(r.verified()))
                  .verifyComplete();
            })
        .verifyComplete();
  }

  @Test
  void tamperedMacFails() {
    SigningMaterial material = sampleMaterial(integrity.newNonce(), "d");
    IntegrityProof proof = integrity.sign(material, profile).block();
    IntegrityProof tampered =
        new IntegrityProof(
            proof.profileRef(),
            proof.algorithm(),
            proof.keyRef(),
            proof.keyVersion(),
            proof.canonicalizationVersion(),
            proof.issuedAt(),
            proof.expiresAt(),
            proof.nonce(),
            proof.payloadDigestAlgorithm(),
            proof.payloadDigest(),
            proof.mac().substring(0, proof.mac().length() - 2) + "aa");
    StepVerifier.create(integrity.verify(material, tampered))
        .assertNext(
            r -> assertEquals(IntegrityVerificationDisposition.INVALID_MAC, r.disposition()))
        .verifyComplete();
  }

  @Test
  void rotationV1StillVerifiesWhenAccepted() {
    IntegrityProfileDefinition rotated =
        new IntegrityProfileDefinition(
            profile.profileCode(),
            profile.version(),
            profile.purpose(),
            profile.algorithm(),
            profile.signingKeyRef(),
            "v2",
            List.of("v1", "v2"),
            profile.canonicalizationVersion(),
            profile.timestampTolerance(),
            true,
            profile.replayWindow(),
            profile.maximumPayloadDigestBytes(),
            IntegrityProfileStatus.PUBLISHED,
            profile.definitionIntegrityRef());
    MessageIntegrityService rotatedSvc =
        new MessageIntegrityService(
            keys,
            new ConfiguredIntegrityProfileCatalog(List.of(rotated)),
            new IntegrityKeyRotationService(),
            SpiderClock.fixed(NOW));
    SigningMaterial material = sampleMaterial(integrity.newNonce(), "d");
    IntegrityProof v1Proof = integrity.sign(material, profile).block();
    assertEquals("v1", v1Proof.keyVersion());
    StepVerifier.create(rotatedSvc.verify(material, v1Proof))
        .assertNext(r -> assertTrue(r.verified()))
        .verifyComplete();
    IntegrityProof v2Proof = rotatedSvc.sign(material, rotated).block();
    assertEquals("v2", v2Proof.keyVersion());
  }

  @Test
  void revokedKeyFails() {
    KeyReference revoked =
        new KeyReference(
            "key:test-callback", "revoked", IntegrityPurpose.CALLBACK_DELIVERY, IntegrityAlgorithm.HMAC_SHA_256);
    StepVerifier.create(keys.resolveForVerification(revoked))
        .expectError(CryptographicKeyException.class)
        .verify();
  }

  @Test
  void handleToStringMasksSecret() {
    KeyReference ref =
        new KeyReference(
            "key:test-callback", "v1", IntegrityPurpose.CALLBACK_DELIVERY, IntegrityAlgorithm.HMAC_SHA_256);
    CryptographicKeyHandle handle = keys.resolveForSigning(ref).block();
    assertFalse(handle.toString().contains("spider-test-key"));
    handle.close();
  }

  @Test
  void payloadDigestChangesWithContent() {
    CanonicalPayloadDigestService dig = new CanonicalPayloadDigestService();
    String a = dig.digestUtf8("abc", 1000);
    String b = dig.digestUtf8("abd", 1000);
    assertNotEquals(a, b);
    assertTrue(dig.secureEquals(a, a));
  }

  private SigningMaterial sampleMaterial(String nonce, String digest) {
    return new SigningMaterial(
        SigningInputCanonicalizerV1.DOMAIN_CALLBACK_DELIVERY,
        profile.exactRef(),
        IntegrityAlgorithm.HMAC_SHA_256,
        "key:test-callback",
        "v1",
        "contract:cb@1",
        "CALLBACK_DELIVERY",
        "e1",
        "logical-cb-1",
        1,
        NOW,
        NOW.plusSeconds(60),
        nonce,
        "SHA-256",
        digest,
        SigningCanonicalizationVersion.SPIDER_SIGNING_INPUT_V1);
  }
}
