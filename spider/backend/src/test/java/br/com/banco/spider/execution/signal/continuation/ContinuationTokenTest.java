package br.com.banco.spider.execution.signal.continuation;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import br.com.banco.spider.execution.fingerprint.Sha256IdempotencyKeyHash;
import br.com.banco.spider.security.integrity.ConfiguredIntegrityProfileCatalog;
import br.com.banco.spider.security.integrity.CryptographicKeyMaterialProviderPort;
import br.com.banco.spider.security.integrity.SensitiveFingerprintService;
import java.security.SecureRandom;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.ObjectProvider;

class ContinuationTokenTest {

  @Test
  void generateHasEntropyAndMaskedToString() {
    ContinuationToken t = ContinuationToken.generate(new SecureRandom());
    assertThat(t.wire()).hasSizeGreaterThanOrEqualTo(40);
    assertThat(t.wire()).doesNotContain("execution");
    assertThat(t.toString()).isEqualTo("ContinuationToken[REDACTED]");
  }

  @Test
  void malformedRejected() {
    assertThatThrownBy(() -> ContinuationToken.parse("short"))
        .isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void fingerprintDeterministicLegacy() {
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
    ContinuationTokenFingerprintService svc =
        new ContinuationTokenFingerprintService(fps, new Sha256IdempotencyKeyHash());
    ContinuationToken t =
        ContinuationToken.parse(
            java.util.Base64.getUrlEncoder().withoutPadding().encodeToString(new byte[32]));
    var a = svc.legacySha(t);
    var b = svc.legacySha(t);
    assertThat(svc.matchesConstantTime(a, b)).isTrue();
  }
}
