package br.com.banco.spider.governance;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.execution.signal.ExternalSignalDefinition;
import br.com.banco.spider.execution.signal.continuation.ContinuationToken;
import br.com.banco.spider.execution.signal.continuation.ContinuationTokenFingerprintService;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.execution.wait.WaitType;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionWaitStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryProtectedSignalEnvelopeStore;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import br.com.banco.spider.security.dataprotection.ProtectedPayloadService;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.security.integrity.ConfiguredIntegrityProfileCatalog;
import br.com.banco.spider.security.integrity.CryptographicKeyMaterialProviderPort;
import br.com.banco.spider.security.integrity.SensitiveFingerprintService;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;

/**
 * E2E consolidado (sem rede): Snapshot V2 com DP → wait com fingerprint (sem token puro) →
 * encrypt com profile do snapshot → store sem plaintext → decrypt com profile histórico.
 */
class ConsolidationDurablePipelineE2ETest {

  @Test
  void snapshotV2TokenFingerprintEncryptDecryptWithoutPlaintextOrRawToken() {
    DataProtectionProfileDefinition dp =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    ExternalSignalDefinition signal =
        ExternalSignalDefinition.publishedMock(
            "async", "1.0", "contract:async", "integrity:sig@1.0", dp.exactRef());

    GovernanceArtifactDigestService digests = new GovernanceArtifactDigestService();
    String counts = "routes=0;retries=0;waits=0;callbacks=0;bindings=0;signals=1;dp=1";
    ActiveGovernanceSnapshot snap =
        new ActiveGovernanceSnapshot(
            "snap-e2e",
            "bundle@1.0",
            "bd-e2e",
            new GovernanceScope("DEFAULT"),
            Instant.parse("2026-08-01T00:00:00Z"),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(),
            Map.of(signal.ref(), signal),
            Map.of(dp.exactRef(), dp),
            digests.digestSnapshot("bundle@1.0", "bd-e2e", counts));

    GovernanceSnapshotCodec codec = new GovernanceSnapshotCodec(digests);
    String encoded = codec.encode(snap);
    assertThat(encoded).contains("GOVERNANCE_SNAPSHOT_V2");
    ActiveGovernanceSnapshot reloaded = codec.decode(encoded);
    assertThat(reloaded.dataProtectionProfiles().get(dp.exactRef()).keyRef())
        .isEqualTo(dp.keyRef());

    // Token → fingerprint only on wait
    ObjectProvider<CryptographicKeyMaterialProviderPort> empty =
        new ObjectProvider<>() {
          @Override
          public CryptographicKeyMaterialProviderPort getObject() {
            return null;
          }

          @Override
          public CryptographicKeyMaterialProviderPort getObject(Object... args) {
            return null;
          }

          @Override
          public CryptographicKeyMaterialProviderPort getIfAvailable() {
            return null;
          }

          @Override
          public CryptographicKeyMaterialProviderPort getIfUnique() {
            return null;
          }
        };
    SensitiveFingerprintService fps =
        new SensitiveFingerprintService(
            empty,
            new ConfiguredIntegrityProfileCatalog(List.of()),
            new Sha256IdempotencyKeyHash(),
            false);
    ContinuationTokenFingerprintService tokenFp =
        new ContinuationTokenFingerprintService(fps, new Sha256IdempotencyKeyHash());
    ContinuationToken token = ContinuationToken.generate(new SecureRandom());
    String wire = token.wire();
    var fp = tokenFp.legacySha(token);
    token.zeroize();

    Instant now = Instant.parse("2026-08-01T01:00:00Z");
    InMemoryExecutionWaitStore waits = new InMemoryExecutionWaitStore();
    ExecutionWaitRecord wait =
        new ExecutionWaitRecord(
            "wait-e2e",
            "exec-e2e",
            "step-1",
            "att-1",
            WaitType.ASYNC_COMPLETION,
            "wait:async@1.0",
            "ext-1",
            signal.contractRef(),
            "source:mock",
            WaitState.WAITING,
            0L,
            now,
            null,
            now.plusSeconds(3600),
            null,
            null,
            null,
            signal.ref(),
            signal.integrityProfileRef(),
            fp.digest(),
            fp.algorithmVersion().name(),
            null,
            null,
            now.plusSeconds(3600),
            dp.exactRef());
    waits.insert(wait);
    assertThat(wait.continuationTokenFingerprint()).isEqualTo(fp.digest());
    assertThat(wait.toString()).doesNotContain(wire);
    assertThat(waits.findByContinuationTokenFingerprint(fp.digest())).isPresent();

    // Encrypt with snapshot profile (not hardcoded)
    DataProtectionProfileDefinition historical =
        reloaded.dataProtectionProfile(wait.dataProtectionProfileRef()).orElseThrow();
    ProtectedPayloadService protect =
        ProtectedPayloadService.forTests(new MockDataProtectionKeyMaterialProvider(), new SecureRandom());
    InMemoryProtectedSignalEnvelopeStore envelopes = new InMemoryProtectedSignalEnvelopeStore();
    byte[] plaintext = ("VERIFIED|" + signal.ref()).getBytes();
    var ctx =
        new ProtectedPayloadService.DataProtectionContext(
            historical,
            "env:e2e",
            wait.executionId(),
            wait.waitId(),
            signal.ref(),
            "VERIFIED_SIGNAL_ENVELOPE_V1",
            now);
    var protectedPayload = protect.protect(plaintext, ctx).block();
    assertThat(protectedPayload).isNotNull();
    envelopes.createOnce(
        new br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelope(
            "pse-e2e",
            "env:e2e",
            historical.exactRef(),
            protectedPayload.algorithm(),
            protectedPayload.keyRef(),
            protectedPayload.keyVersion(),
            protectedPayload.aadVersion(),
            protectedPayload.iv(),
            protectedPayload.ciphertextAndTag(),
            "ptd",
            "ctd",
            protectedPayload.plaintextSize(),
            br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState.AVAILABLE,
            now,
            null,
            null,
            null,
            null,
            0L));

    var stored = envelopes.findByInboxLogicalKey("env:e2e").orElseThrow();
    assertThat(new String(stored.ciphertextAndTag())).doesNotContain("VERIFIED|");
    assertThat(stored.toString()).doesNotContain("VERIFIED|");

    // "Restart": new store reference reading same ciphertext + historical profile from V2
    byte[] roundTrip =
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
                new ProtectedPayloadService.DataProtectionContext(
                    historical,
                    "env:e2e",
                    wait.executionId(),
                    wait.waitId(),
                    signal.ref(),
                    "VERIFIED_SIGNAL_ENVELOPE_V1",
                    stored.createdAt()))
            .block();
    assertThat(new String(roundTrip)).isEqualTo("VERIFIED|" + signal.ref());
  }
}
