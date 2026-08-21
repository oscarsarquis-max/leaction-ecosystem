package br.com.banco.spider.security.dataprotection;

import java.util.Optional;

public interface DataProtectionProfileCatalogPort {
  Optional<DataProtectionProfileDefinition> findPublished(String exactRef);

  Optional<DataProtectionProfileDefinition> findByCodeVersion(String code, String version);
}
