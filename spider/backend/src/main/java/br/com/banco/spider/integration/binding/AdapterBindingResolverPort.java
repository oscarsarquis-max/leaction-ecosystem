package br.com.banco.spider.integration.binding;

import reactor.core.publisher.Mono;

public interface AdapterBindingResolverPort {
  Mono<AdapterBindingResolution> resolve(String adapterBindingRef);
}
