package br.com.banco.spider.governance.port;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import java.util.Optional;

public interface GovernanceSnapshotStorePort {
  ActiveGovernanceSnapshot insert(ActiveGovernanceSnapshot snapshot);

  Optional<ActiveGovernanceSnapshot> findSnapshotById(String snapshotId);

  Optional<ActiveGovernanceSnapshot> findByBundleRefAndDigest(String bundleRef, String digest);
}
