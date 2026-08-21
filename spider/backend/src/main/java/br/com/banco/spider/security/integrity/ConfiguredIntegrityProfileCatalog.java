package br.com.banco.spider.security.integrity;

import java.util.List;
import java.util.Map;
import java.util.Optional;

public final class ConfiguredIntegrityProfileCatalog implements IntegrityProfileCatalogPort {

  private final Map<String, IntegrityProfileDefinition> byRef;

  public ConfiguredIntegrityProfileCatalog(List<IntegrityProfileDefinition> profiles) {
    Map<String, IntegrityProfileDefinition> map = new java.util.LinkedHashMap<>();
    for (IntegrityProfileDefinition p :
        profiles == null ? List.<IntegrityProfileDefinition>of() : profiles) {
      map.put(p.exactRef(), p);
    }
    this.byRef = Map.copyOf(map);
  }

  @Override
  public Optional<IntegrityProfileDefinition> findByExactRef(String exactRef) {
    return Optional.ofNullable(byRef.get(exactRef));
  }

  @Override
  public Optional<IntegrityProfileDefinition> findPublished(
      String exactRef, IntegrityPurpose purpose) {
    return findByExactRef(exactRef)
        .filter(p -> p.purpose() == purpose)
        .filter(IntegrityProfileDefinition::canSign);
  }
}
