package br.com.banco.spider.execution.signal;

import static org.assertj.core.api.Assertions.assertThat;

import br.com.banco.spider.execution.signal.continuation.ContinuationToken;
import br.com.banco.spider.execution.signal.continuation.ContinuationTokenFingerprintService;
import br.com.banco.spider.execution.signal.continuation.ContinuationTokenWaitResolver;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.execution.wait.WaitType;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionWaitStore;
import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.security.integrity.ConfiguredIntegrityProfileCatalog;
import br.com.banco.spider.security.integrity.CryptographicKeyMaterialProviderPort;
import br.com.banco.spider.security.integrity.SensitiveFingerprintService;
import java.security.SecureRandom;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;
import reactor.test.StepVerifier;

/** E2E leve: token → fingerprint → lookup; sem plaintext no wait. */
class DurableTokenLookupE2ETest {

  @Test
  void tokenLookupFindsWaitWithoutPersistingRawToken() {
    InMemoryExecutionWaitStore waits = new InMemoryExecutionWaitStore();
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
    ContinuationTokenWaitResolver resolver =
        new ContinuationTokenWaitResolver(waits, tokenFp, true, true);

    ContinuationToken token = ContinuationToken.generate(new SecureRandom());
    String wire = token.wire();
    var fp = tokenFp.legacySha(token);
    token.zeroize();

    Instant now = Instant.parse("2026-07-01T10:00:00Z");
    ExecutionWaitRecord wait =
        new ExecutionWaitRecord(
            "wait-1",
            "exec-1",
            "step-1",
            "att-1",
            WaitType.ASYNC_COMPLETION,
            "wait:async@1.0",
            "ext-1",
            "contract:mock",
            "source:mock",
            WaitState.WAITING,
            0L,
            now,
            null,
            now.plusSeconds(3600),
            null,
            null,
            null,
            null,
            null,
            fp.digest(),
            fp.algorithmVersion().name(),
            null,
            null,
            now.plusSeconds(3600),
            null);
    waits.insert(wait);

    assertThat(wait.continuationTokenFingerprint()).isEqualTo(fp.digest());
    assertThat(wait.toString()).doesNotContain(wire);

    StepVerifier.create(resolver.resolveByToken(wire, now))
        .assertNext(opt -> assertThat(opt).isPresent().get().extracting(ExecutionWaitRecord::waitId).isEqualTo("wait-1"))
        .verifyComplete();

    StepVerifier.create(resolver.resolveByToken("not-a-valid-token!!!!!!!!!!!!!", now))
        .assertNext(opt -> assertThat(opt).isEmpty())
        .verifyComplete();
  }
}
