package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.governance.GovernanceLifecycleState;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileCatalogPort;
import br.com.banco.spider.security.dataprotection.DataProtectionProfileDefinition;
import java.util.Objects;
import java.util.Optional;

public final class SnapshotBackedDataProtectionProfileCatalog
    implements DataProtectionProfileCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedDataProtectionProfileCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = Objects.requireNonNull(snapshot, "snapshot");
  }

  @Override
  public Optional<DataProtectionProfileDefinition> findPublished(String exactRef) {
    if (exactRef == null || exactRef.isBlank()) {
      return Optional.empty();
    }
    String key = exactRef.trim();
    DataProtectionProfileDefinition p = snapshot.dataProtectionProfiles().get(key);
    if (p == null) {
      p =
          snapshot.dataProtectionProfiles().values().stream()
              .filter(d -> d.exactRef().equals(key) || (d.profileCode() + "@" + d.version()).equals(key))
              .findFirst()
              .orElse(null);
    }
    if (p == null || p.status() != GovernanceLifecycleState.PUBLISHED) {
      return Optional.empty();
    }
    return Optional.of(p);
  }

  @Override
  public Optional<DataProtectionProfileDefinition> findByCodeVersion(String code, String version) {
    return findPublished("dp:" + code + "@" + version);
  }
}
