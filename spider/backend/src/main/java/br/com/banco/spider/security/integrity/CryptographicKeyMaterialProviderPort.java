package br.com.banco.spider.security.integrity;

import reactor.core.publisher.Mono;

public interface CryptographicKeyMaterialProviderPort {
  Mono<CryptographicKeyHandle> resolveForSigning(KeyReference reference);

  Mono<CryptographicKeyHandle> resolveForVerification(KeyReference reference);
}
