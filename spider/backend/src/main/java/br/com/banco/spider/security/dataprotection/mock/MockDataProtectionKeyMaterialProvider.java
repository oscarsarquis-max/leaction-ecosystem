package br.com.banco.spider.security.dataprotection.mock;

import br.com.banco.spider.security.dataprotection.DataProtectionAlgorithm;
import br.com.banco.spider.security.dataprotection.DataProtectionKeyHandle;
import br.com.banco.spider.security.dataprotection.DataProtectionKeyMaterialProviderPort;
import br.com.banco.spider.security.dataprotection.DataProtectionKeyReference;
import br.com.banco.spider.security.dataprotection.DataProtectionPurpose;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Map;
import java.util.Set;
import reactor.core.publisher.Mono;

/** Somente teste / flag explícita — chaves determinísticas, sem log de bytes. */
public final class MockDataProtectionKeyMaterialProvider
    implements DataProtectionKeyMaterialProviderPort {

  private final Set<String> revoked = Set.of("revoked");
  private final Map<String, String> aliases =
      Map.of(
          "key:dp:signal-envelope@v1", "v1",
          "key:dp:signal-envelope@v2", "v2");

  @Override
  public Mono<DataProtectionKeyHandle> resolveForEncryption(DataProtectionKeyReference ref) {
    return resolve(ref, true);
  }

  @Override
  public Mono<DataProtectionKeyHandle> resolveForDecryption(DataProtectionKeyReference ref) {
    return resolve(ref, false);
  }

  private Mono<DataProtectionKeyHandle> resolve(DataProtectionKeyReference ref, boolean encrypt) {
    if (ref.purpose() != DataProtectionPurpose.EXTERNAL_SIGNAL_ENVELOPE_AT_REST
        || ref.algorithm() != DataProtectionAlgorithm.AES_256_GCM) {
      return Mono.error(new IllegalStateException("KEY_PURPOSE_MISMATCH"));
    }
    if (revoked.contains(ref.keyVersion())) {
      return Mono.error(new IllegalStateException("KEY_REVOKED"));
    }
    if (!aliases.containsKey(ref.keyRef()) && !ref.keyRef().startsWith("key:dp:")) {
      return Mono.error(new IllegalStateException("KEY_NOT_FOUND"));
    }
    try {
      MessageDigest md = MessageDigest.getInstance("SHA-256");
      byte[] key =
          md.digest(
              ("MOCK-DP|" + ref.keyRef() + "|" + ref.keyVersion())
                  .getBytes(StandardCharsets.UTF_8));
      return Mono.just(
          new DataProtectionKeyHandle(
              ref.keyRef(), ref.keyVersion(), DataProtectionAlgorithm.AES_256_GCM, key));
    } catch (Exception ex) {
      return Mono.error(new IllegalStateException("KEY_UNAVAILABLE"));
    }
  }
}
