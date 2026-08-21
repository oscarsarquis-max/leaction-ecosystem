package br.com.banco.spider.security.integrity.mock;

import br.com.banco.spider.security.integrity.CryptoKeyFailureCode;
import br.com.banco.spider.security.integrity.CryptographicKeyException;
import br.com.banco.spider.security.integrity.CryptographicKeyHandle;
import br.com.banco.spider.security.integrity.CryptographicKeyMaterialProviderPort;
import br.com.banco.spider.security.integrity.IntegrityAlgorithm;
import br.com.banco.spider.security.integrity.IntegrityPurpose;
import br.com.banco.spider.security.integrity.KeyReference;
import java.nio.charset.StandardCharsets;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import reactor.core.publisher.Mono;

/**
 * Mock Key Material Provider — somente testes/perfil Mock. Material determinístico não produtivo.
 * Não é bean por default.
 */
public final class MockCryptographicKeyMaterialProvider
    implements CryptographicKeyMaterialProviderPort {

  public enum Scenario {
    NORMAL,
    UNAVAILABLE,
    NOT_FOUND
  }

  private final Map<String, byte[]> materialByVersion;
  private final Set<String> revokedVersions;
  private final Scenario scenario;

  public MockCryptographicKeyMaterialProvider() {
    this(Scenario.NORMAL);
  }

  public MockCryptographicKeyMaterialProvider(Scenario scenario) {
    this.scenario = Objects.requireNonNull(scenario);
    // Chaves claramente de teste — nunca usar em produção
    this.materialByVersion =
        Map.of(
            "v1", "spider-test-key-material-v1-not-for-prod".getBytes(StandardCharsets.UTF_8),
            "v2", "spider-test-key-material-v2-not-for-prod".getBytes(StandardCharsets.UTF_8));
    this.revokedVersions = Set.of("revoked");
  }

  @Override
  public Mono<CryptographicKeyHandle> resolveForSigning(KeyReference reference) {
    return resolve(reference, true);
  }

  @Override
  public Mono<CryptographicKeyHandle> resolveForVerification(KeyReference reference) {
    return resolve(reference, false);
  }

  private Mono<CryptographicKeyHandle> resolve(KeyReference reference, boolean signing) {
    if (scenario == Scenario.UNAVAILABLE) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.KEY_UNAVAILABLE));
    }
    if (scenario == Scenario.NOT_FOUND) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.KEY_NOT_FOUND));
    }
    if (reference.algorithm() != IntegrityAlgorithm.HMAC_SHA_256) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.ALGORITHM_MISMATCH));
    }
    if (revokedVersions.contains(reference.keyVersion())) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.KEY_REVOKED));
    }
    byte[] bytes = materialByVersion.get(reference.keyVersion());
    if (bytes == null) {
      return Mono.error(new CryptographicKeyException(CryptoKeyFailureCode.KEY_NOT_FOUND));
    }
    // purpose is recorded on KeyReference; mock accepts all IntegrityPurpose values for tests
    Objects.requireNonNull(reference.purpose());
    return Mono.just(new CryptographicKeyHandle(reference, bytes));
  }
}
