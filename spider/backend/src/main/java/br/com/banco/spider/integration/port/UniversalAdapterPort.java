package br.com.banco.spider.integration.port;

import reactor.core.publisher.Mono;

/**
 * Porta universal Engine–Adapter (SPIDER-ARCH-006).
 * Neutra a transporte; abstração reativa alinhada ao WebFlux sem expor WebClient.
 */
public interface UniversalAdapterPort {

  Mono<UniversalAdapterResult> invoke(UniversalAdapterRequest request);
}
