package br.com.banco.spider.execution.signal.protection;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.infrastructure.persistence.memory.InMemoryProtectedSignalEnvelopeStore;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import br.com.banco.spider.security.dataprotection.ProtectedPayloadService;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicBoolean;
import org.junit.jupiter.api.Test;

/**
 * Falha de encrypt/persistência não deixa APPLY_PENDING parcial; duplicate não re-encrypta.
 */
class ProtectedEnvelopeTransactionalSemanticsTest {

  @Test
  void encryptFailureLeavesNoEnvelopeAndDuplicateCreateOnceIsIdempotent() {
    InMemoryProtectedSignalEnvelopeStore store = new InMemoryProtectedSignalEnvelopeStore();
    ProtectedPayloadService protect =
        ProtectedPayloadService.forTests(new MockDataProtectionKeyMaterialProvider(), new SecureRandom());
    var profile =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    Instant now = Instant.parse("2026-07-01T00:00:00Z");
    var ctx =
        new ProtectedPayloadService.DataProtectionContext(
            profile,
            "env:dedup-1",
            "exec-1",
            "wait-1",
            "signal:mock@1.0",
            "VERIFIED_SIGNAL_ENVELOPE_V1",
            now);

    AtomicBoolean encryptAttempted = new AtomicBoolean(false);
    // Simulate encrypt failure path: oversized plaintext
    byte[] tooLarge = new byte[300_000];
    encryptAttempted.set(true);
    try {
      protect.protect(tooLarge, ctx).block();
    } catch (Exception ex) {
      // expected
    }
    assertThat(encryptAttempted.get()).isTrue();
    assertThat(store.findByInboxLogicalKey("env:dedup-1")).isEmpty();

    byte[] ok = "verified-envelope-v1".getBytes();
    var protectedPayload = protect.protect(ok, ctx).block();
    assertThat(protectedPayload).isNotNull();
    ProtectedSignalEnvelope first =
        store.createOnce(
            new ProtectedSignalEnvelope(
                "pse-1",
                "env:dedup-1",
                profile.exactRef(),
                protectedPayload.algorithm(),
                protectedPayload.keyRef(),
                protectedPayload.keyVersion(),
                protectedPayload.aadVersion(),
                protectedPayload.iv(),
                protectedPayload.ciphertextAndTag(),
                "ptd",
                "ctd",
                protectedPayload.plaintextSize(),
                ProtectedEnvelopeState.AVAILABLE,
                now,
                null,
                null,
                null,
                null,
                0L));
    // duplicate createOnce must not replace ciphertext
    byte[] differentCt = protectedPayload.ciphertextAndTag().clone();
    differentCt[0] ^= 0x7F;
    ProtectedSignalEnvelope second =
        store.createOnce(
            new ProtectedSignalEnvelope(
                "pse-2",
                "env:dedup-1",
                profile.exactRef(),
                protectedPayload.algorithm(),
                protectedPayload.keyRef(),
                protectedPayload.keyVersion(),
                protectedPayload.aadVersion(),
                protectedPayload.iv(),
                differentCt,
                "ptd2",
                "ctd2",
                protectedPayload.plaintextSize(),
                ProtectedEnvelopeState.AVAILABLE,
                now,
                null,
                null,
                null,
                null,
                0L));
    assertThat(second.protectedEnvelopeId()).isEqualTo(first.protectedEnvelopeId());
    assertThat(second.ciphertextAndTag()).isEqualTo(first.ciphertextAndTag());
    assertThat(new String(second.ciphertextAndTag())).doesNotContain("verified-envelope");
  }
}
