package br.com.banco.spider.governance.catalog;

import br.com.banco.spider.governance.ActiveGovernanceSnapshot;
import br.com.banco.spider.security.integrity.IntegrityProfileCatalogPort;
import br.com.banco.spider.security.integrity.IntegrityProfileDefinition;
import br.com.banco.spider.security.integrity.IntegrityPurpose;
import java.util.Optional;

public final class SnapshotBackedIntegrityProfileCatalog implements IntegrityProfileCatalogPort {

  private final ActiveGovernanceSnapshot snapshot;

  public SnapshotBackedIntegrityProfileCatalog(ActiveGovernanceSnapshot snapshot) {
    this.snapshot = snapshot;
  }

  @Override
  public Optional<IntegrityProfileDefinition> findByExactRef(String exactRef) {
    return Optional.ofNullable(snapshot.integrityProfiles().get(exactRef));
  }

  @Override
  public Optional<IntegrityProfileDefinition> findPublished(
      String exactRef, IntegrityPurpose purpose) {
    return findByExactRef(exactRef)
        .filter(p -> purpose == null || purpose.equals(p.purpose()));
  }
}
