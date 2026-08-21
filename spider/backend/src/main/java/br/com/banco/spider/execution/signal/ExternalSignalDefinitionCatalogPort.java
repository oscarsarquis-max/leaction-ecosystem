package br.com.banco.spider.execution.signal;

import java.util.Optional;

public interface ExternalSignalDefinitionCatalogPort {
  Optional<ExternalSignalDefinition> findByExactRef(String exactRef);
}
