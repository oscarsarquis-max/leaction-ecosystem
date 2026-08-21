package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.governance.port.GovernanceRevocationRegistryPort;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryGovernanceRevocationRegistry implements GovernanceRevocationRegistryPort {

  private final Map<String, String> revoked = new ConcurrentHashMap<>();

  @Override
  public boolean isSnapshotRevoked(String snapshotId) {
    return snapshotId != null && revoked.containsKey(snapshotId);
  }

  @Override
  public void markRevoked(String snapshotId, String reasonCode) {
    if (snapshotId != null) {
      revoked.put(snapshotId, reasonCode == null ? "REVOKED" : reasonCode);
    }
  }
}
