package br.com.banco.spider.security.dataprotection;

import reactor.core.publisher.Mono;

public interface DataProtectionKeyMaterialProviderPort {
  Mono<DataProtectionKeyHandle> resolveForEncryption(DataProtectionKeyReference ref);

  Mono<DataProtectionKeyHandle> resolveForDecryption(DataProtectionKeyReference ref);
}
