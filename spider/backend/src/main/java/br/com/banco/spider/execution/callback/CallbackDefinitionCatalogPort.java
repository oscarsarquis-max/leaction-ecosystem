package br.com.banco.spider.execution.callback;

import java.util.List;
import java.util.Optional;

public interface CallbackDefinitionCatalogPort {
  Optional<CallbackDefinition> findByExactRef(String exactRef);

  List<CallbackDefinition> allPublished();
}
