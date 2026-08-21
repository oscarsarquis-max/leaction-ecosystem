package br.com.banco.spider.infrastructure.persistence.jpa;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.execution.signal.protection.ProtectedEnvelopeState;
import br.com.banco.spider.execution.signal.protection.ProtectedSignalEnvelope;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.execution.wait.WaitType;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionWaitEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ProtectedSignalEnvelopeEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionWaitJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ProtectedSignalEnvelopeJpaRepository;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import br.com.banco.spider.security.dataprotection.ProtectedPayloadService;
import br.com.banco.spider.security.dataprotection.mock.MockDataProtectionKeyMaterialProvider;
import java.security.SecureRandom;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.domain.EntityScan;
import org.springframework.boot.test.autoconfigure.orm.jpa.DataJpaTest;
import org.springframework.data.jpa.repository.config.EnableJpaRepositories;
import org.springframework.test.context.TestPropertySource;

/**
 * E2E JPA/H2: wait fingerprint + protected envelope ciphertext round-trip; sem token/plaintext.
 */
@DataJpaTest
@EntityScan(basePackageClasses = {ExecutionWaitEntity.class, ProtectedSignalEnvelopeEntity.class})
@EnableJpaRepositories(
    basePackageClasses = {
      ExecutionWaitJpaRepository.class,
      ProtectedSignalEnvelopeJpaRepository.class
    })
@TestPropertySource(
    properties = {
      "spring.datasource.url=jdbc:h2:mem:spider_consol_datajpa;MODE=PostgreSQL;DB_CLOSE_DELAY=-1",
      "spring.datasource.driver-class-name=org.h2.Driver",
      "spring.datasource.username=sa",
      "spring.datasource.password=",
      "spring.jpa.hibernate.ddl-auto=create-drop",
      "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect"
    })
class ConsolidationJpaProtectedEnvelopeE2ETest {

  @Autowired ExecutionWaitJpaRepository waitRepo;
  @Autowired ProtectedSignalEnvelopeJpaRepository envelopeRepo;

  @Test
  void jpaPersistsFingerprintAndCiphertextOnlyThenDecryptsAfterReload() {
    Instant now = Instant.parse("2026-08-21T12:00:00Z");
    String rawToken = "RAW-TOKEN-MUST-NOT-APPEAR";

    ExecutionWaitEntity wait = new ExecutionWaitEntity();
    wait.setWaitId("wait-jpa-e2e");
    wait.setExecutionId("exec-jpa");
    wait.setStepId("step-1");
    wait.setAttemptId("att-1");
    wait.setWaitType(WaitType.ASYNC_COMPLETION);
    wait.setWaitPolicyRef("wait:async@1.0");
    wait.setExternalOperationRef("ext-1");
    wait.setExpectedSignalContractRef("contract:async");
    wait.setExpectedSourceRef("source:mock");
    wait.setState(WaitState.WAITING);
    wait.setStateVersion(0L);
    wait.setCreatedAt(now);
    wait.setExpiresAt(now.plusSeconds(3600));
    wait.setContinuationTokenFingerprint("fp-" + Math.abs(rawToken.hashCode()));
    wait.setContinuationTokenFingerprintVersion("V1_SHA256");
    wait.setContinuationTokenExpiresAt(now.plusSeconds(3600));
    wait.setDataProtectionProfileRef("dp:signal-envelope@1.0");
    waitRepo.saveAndFlush(wait);

    ExecutionWaitEntity loadedWait = waitRepo.findById("wait-jpa-e2e").orElseThrow();
    assertThat(loadedWait.getContinuationTokenFingerprint()).startsWith("fp-");
    assertThat(loadedWait.getContinuationTokenFingerprint()).doesNotContain(rawToken);
    assertThat(loadedWait.getDataProtectionProfileRef()).isEqualTo("dp:signal-envelope@1.0");

    var profile =
        DataProtectionProfileDefinition.publishedAes256(
            "signal-envelope", "1.0", "key:dp:signal-envelope@v1", "v1");
    ProtectedPayloadService protect =
        ProtectedPayloadService.forTests(new MockDataProtectionKeyMaterialProvider(), new SecureRandom());
    byte[] plaintext = "SENSITIVE-PLAINTEXT-PAYLOAD".getBytes();
    var pctx =
        new ProtectedPayloadService.DataProtectionContext(
            profile,
            "env:jpa-e2e",
            "exec-jpa",
            "wait-jpa-e2e",
            "signal:async@1.0",
            "VERIFIED_SIGNAL_ENVELOPE_V1",
            now);
    var protectedPayload = protect.protect(plaintext, pctx).block();
    assertThat(protectedPayload).isNotNull();

    JpaProtectedSignalEnvelopeStoreAdapter adapter =
        new JpaProtectedSignalEnvelopeStoreAdapter(envelopeRepo);
    adapter.createOnce(
        new ProtectedSignalEnvelope(
            "pse-jpa-e2e",
            "env:jpa-e2e",
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

    ProtectedSignalEnvelopeEntity entity =
        envelopeRepo.findByInboxLogicalKey("env:jpa-e2e").orElseThrow();
    assertThat(entity.getCiphertextAndTagB64()).doesNotContain("SENSITIVE-PLAINTEXT");
    assertThat(entity.getIvB64()).isNotBlank();

    ProtectedSignalEnvelope reloaded = adapter.findByInboxLogicalKey("env:jpa-e2e").orElseThrow();
    byte[] decrypted =
        protect
            .unprotect(
                new ProtectedPayloadService.ProtectedPayload(
                    reloaded.algorithm(),
                    reloaded.keyRef(),
                    reloaded.keyVersion(),
                    reloaded.aadVersion(),
                    reloaded.iv(),
                    reloaded.ciphertextAndTag(),
                    reloaded.plaintextSize()),
                pctx)
            .block();
    assertThat(new String(decrypted)).isEqualTo("SENSITIVE-PLAINTEXT-PAYLOAD");
  }
}
