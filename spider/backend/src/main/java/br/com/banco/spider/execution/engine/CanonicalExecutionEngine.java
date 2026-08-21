package br.com.banco.spider.execution.engine;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import reactor.core.publisher.Mono;

/** Porta de aplicação da Engine canônica mínima. */
public interface CanonicalExecutionEngine {
  Mono<CanonicalExecutionResult> execute(CanonicalExecutionRequest request);

  default Mono<CanonicalExecutionResult> execute(
      CanonicalExecutionRequest request, String ownerPrincipalRef) {
    return execute(request);
  }
}
