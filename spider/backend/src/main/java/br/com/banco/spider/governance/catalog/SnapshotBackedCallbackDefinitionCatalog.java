package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.callback.CallbackDefinition;
import br.com.banco.spider.execution.callback.CallbackDefinitionCatalogPort;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.List;
import java.util.Optional;

public final class SnapshotBackedCallbackDefinitionCatalog implements CallbackDefinitionCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedCallbackDefinitionCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Optional<CallbackDefinition> findByExactRef(String exactRef) {
    return Optional.ofNullable(snapshot.callbackDefinitions().get(exactRef));
  }

  @Override
  public List<CallbackDefinition> allPublished() {
    return List.copyOf(snapshot.callbackDefinitions().values());
  }
}
