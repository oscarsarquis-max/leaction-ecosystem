package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.execution.signal.ExternalSignalDefinition;
import br.com.banco.spider.execution.signal.ExternalSignalDefinitionCatalogPort;
import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceLifecycleState;
import java.util.Objects;
import java.util.Optional;

public final class SnapshotBackedExternalSignalDefinitionCatalog
    implements ExternalSignalDefinitionCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedExternalSignalDefinitionCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = Objects.requireNonNull(snapshot, "snapshot");
  }

  @Override
  public Optional<ExternalSignalDefinition> findByExactRef(String exactRef) {
    if (exactRef == null || exactRef.isBlank()) {
      return Optional.empty();
    }
    String key = exactRef.trim();
    Optional<ExternalSignalDefinition> direct =
        snapshot
            .externalSignal(key)
            .filter(d -> d.status() == GovernanceLifecycleState.PUBLISHED);
    if (direct.isPresent()) {
      return direct;
    }
    return snapshot.externalSignalDefinitions().values().stream()
        .filter(d -> d.status() == GovernanceLifecycleState.PUBLISHED)
        .filter(d -> d.ref().equals(key) || (d.signalCode() + "@" + d.version()).equals(key))
        .findFirst();
  }
}
