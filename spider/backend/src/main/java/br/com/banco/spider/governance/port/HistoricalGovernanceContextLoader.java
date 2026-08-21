package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.GovernedWorkItemRef;
import br.com.banco.spider.governance.GovernanceResolutionContext;
import reactor.core.publisher.Mono;

public interface HistoricalGovernanceContextLoader {
  Mono<GovernanceResolutionContext> loadForExecution(String executionId);

  Mono<GovernanceResolutionContext> loadForWorkItem(GovernedWorkItemRef ref);
}
