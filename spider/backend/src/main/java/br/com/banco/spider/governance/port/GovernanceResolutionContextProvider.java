package br.com.banco.spider.governance.port;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.governance.GovernanceResolutionContext;
import reactor.core.publisher.Mono;

public interface GovernanceResolutionContextProvider {
  Mono<GovernanceResolutionContext> resolveForNewExecution(CanonicalExecutionRequest request);

  Mono<GovernanceResolutionContext> resolveForExistingExecution(String executionId);
}
