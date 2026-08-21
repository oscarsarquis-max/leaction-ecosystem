package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceScope;
import reactor.core.publisher.Mono;

public interface ActiveGovernanceSnapshotProviderPort {
  Mono<ActiveGovernanceSnapshot> getActiveSnapshot(GovernanceScope scope);

  Mono<ActiveGovernanceSnapshot> getSnapshot(String snapshotId);

  /** Refresh idempotente para outra instância — sem scheduler. */
  Mono<ActiveGovernanceSnapshot> refreshActive(GovernanceScope scope);

  void putAfterCommit(GovernanceScope scope, ActiveGovernanceSnapshot snapshot);
}
