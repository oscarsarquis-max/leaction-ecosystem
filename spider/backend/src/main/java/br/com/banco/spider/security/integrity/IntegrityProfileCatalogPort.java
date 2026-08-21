package br.com.banco.spider.security.integrity;

import java.util.Optional;

public interface IntegrityProfileCatalogPort {
  Optional<IntegrityProfileDefinition> findByExactRef(String exactRef);

  Optional<IntegrityProfileDefinition> findPublished(String exactRef, IntegrityPurpose purpose);
}
