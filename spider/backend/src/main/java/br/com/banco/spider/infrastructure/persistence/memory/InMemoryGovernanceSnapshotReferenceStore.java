package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.governance.port.GovernanceSnapshotReferenceStorePort;

public class InMemoryGovernanceSnapshotReferenceStore
    implements GovernanceSnapshotReferenceStorePort {

  private final ExecutionGovernanceFixationStorePort fixationStore;

  public InMemoryGovernanceSnapshotReferenceStore(
      ExecutionGovernanceFixationStorePort fixationStore,
      ExecutionWaitStorePort waitStore,
      CallbackOutboxStorePort outboxStore,
      CallbackReconciliationStorePort reconciliationStore) {
    this.fixationStore = fixationStore;
  }

  @Override
  public boolean isReferencedByActiveWork(String snapshotId) {
    return countFixations(snapshotId) > 0;
  }

  @Override
  public long countFixations(String snapshotId) {
    return snapshotId == null || fixationStore == null ? 0 : 1;
  }
}
