package br.com.banco.spider.execution.signal.protection;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import br.com.banco.spider.execution.signal.SignalCompletion;
import br.com.banco.spider.execution.signal.SignalSecurityContext;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryProtectedSignalEnvelopeStore;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import br.com.banco.spider.security.dataprotection.ProtectedPayloadService;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;

class ProtectedEnvelopeRoundTripTest {

  @Test
  void storePersistsCiphertextOnly() {
    VerifiedSignalEnvelopeCodec codec = new VerifiedSignalEnvelopeCodec();
    ProtectedPayloadService protect =
        ProtectedPayloadService.forTests(new MockDataProtectionKeyMaterialProvider(), new SecureRandom());
    InMemoryProtectedSignalEnvelopeStore store = new InMemoryProtectedSignalEnvelopeStore();
    Sha256IdempotencyKeyHash sha = new Sha256IdempotencyKeyHash();

    Instant now = Instant.parse("2026-06-01T12:00:00Z");
    ExternalSignalEnvelope envelope =
        new ExternalSignalEnvelope(
            "1.0",
            "msg-1",
            "source:mock",
            "binding:mock",
            "contract:mock",
            "exec-1",
            "step-1",
            "ext-1",
            now,
            now,
            "corr-1",
            null,
            new SignalSecurityContext(
                "p", "source:mock", "MOCK", now, now.plusSeconds(60), "profile:mock", null),
            new SignalCompletion(
                AdapterDispositionMode.COMPLETED,
                CanonicalOutcome.technical(TechnicalStatus.SUCCESS),
                List.of(),
                List.of()));

    byte[] plaintext = codec.encode(envelope, now);
    var profile =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    var ctx =
        new ProtectedPayloadService.DataProtectionContext(
            profile,
            "env:dedup",
            "exec-1",
            "wait-1",
            "signal:mock@1.0",
            "VERIFIED_SIGNAL_ENVELOPE_V1",
            now);
    var protectedPayload = protect.protect(plaintext, ctx).block();
    assertThat(protectedPayload).isNotNull();

    ProtectedSignalEnvelope stored =
        store.createOnce(
            new ProtectedSignalEnvelope(
                "pse-1",
                "env:dedup",
                profile.exactRef(),
                protectedPayload.algorithm(),
                protectedPayload.keyRef(),
                protectedPayload.keyVersion(),
                protectedPayload.aadVersion(),
                protectedPayload.iv(),
                protectedPayload.ciphertextAndTag(),
                sha.hash("pt"),
                sha.hash("ct"),
                protectedPayload.plaintextSize(),
                ProtectedEnvelopeState.AVAILABLE,
                now,
                null,
                null,
                null,
                null,
                0L));

    assertThat(stored.toString()).doesNotContain("msg-1");
    assertThat(new String(stored.ciphertextAndTag())).doesNotContain("msg-1");

    byte[] decrypted =
        protect
            .unprotect(
                new ProtectedPayloadService.ProtectedPayload(
                    stored.algorithm(),
                    stored.keyRef(),
                    stored.keyVersion(),
                    stored.aadVersion(),
                    stored.iv(),
                    stored.ciphertextAndTag(),
                    stored.plaintextSize()),
                ctx)
            .block();
    assertThat(codec.decode(decrypted).messageId()).isEqualTo("msg-1");
  }
}
