package br.com.banco.spider.execution.route;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import reactor.core.publisher.Mono;

public interface RouteResolverPort {
  Mono<RouteResolution> resolve(CanonicalExecutionRequest request);
}
