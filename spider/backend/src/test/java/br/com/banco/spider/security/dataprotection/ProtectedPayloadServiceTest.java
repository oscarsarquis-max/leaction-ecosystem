package br.com.banco.spider.security.dataprotection;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.Arrays;
import org.junit.jupiter.api.Test;
import reactor.test.StepVerifier;

class ProtectedPayloadServiceTest {

  @Test
  void aesGcmRoundTripAndTamperFails() {
    ProtectedPayloadService svc =
        ProtectedPayloadService.forTests(new MockDataProtectionKeyMaterialProvider(), new SecureRandom());

    var profile =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    var ctx =
        new ProtectedPayloadService.DataProtectionContext(
            profile,
            "inbox-1",
            "exec-1",
            "wait-1",
            "signal:mock@1.0",
            "VERIFIED_SIGNAL_ENVELOPE_V1",
            Instant.parse("2026-01-01T00:00:00Z"));
    byte[] plaintext = "hello-envelope".getBytes(StandardCharsets.UTF_8);

    ProtectedPayloadService.ProtectedPayload protectedPayload =
        svc.protect(plaintext, ctx).block();
    assertThat(protectedPayload).isNotNull();
    assertThat(protectedPayload.iv()).hasSize(12);
    assertThat(new String(protectedPayload.ciphertextAndTag(), StandardCharsets.UTF_8))
        .doesNotContain("hello-envelope");

    byte[] roundTrip = svc.unprotect(protectedPayload, ctx).block();
    assertThat(roundTrip).isEqualTo(plaintext);

    byte[] tampered =
        Arrays.copyOf(protectedPayload.ciphertextAndTag(), protectedPayload.ciphertextAndTag().length);
    tampered[0] ^= 0x01;
    var tamperedPayload =
        new ProtectedPayloadService.ProtectedPayload(
            protectedPayload.algorithm(),
            protectedPayload.keyRef(),
            protectedPayload.keyVersion(),
            protectedPayload.aadVersion(),
            protectedPayload.iv(),
            tampered,
            protectedPayload.plaintextSize());
    StepVerifier.create(svc.unprotect(tamperedPayload, ctx)).expectError().verify();
  }

  @Test
  void keyHandleToStringHasNoKeyBytes() {
    DataProtectionKeyHandle handle =
        new DataProtectionKeyHandle(
            "key:dp:signal-envelope@v1",
            "v1",
            DataProtectionAlgorithm.AES_256_GCM,
            new byte[32]);
    assertThat(handle.toString()).contains("key:dp:signal-envelope@v1");
    handle.close();
    assertThatThrownBy(handle::keyMaterialCopy).isInstanceOf(IllegalStateException.class);
  }
}
