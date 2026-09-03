package br.com.banco.spider.context.domain;

import java.util.List;
import java.util.Optional;

public interface BusinessIntentCatalog {
  List<BusinessIntentDefinition> list();

  default List<BusinessIntentDefinition> listBusinessCards() {
    return list().stream().filter(BusinessIntentDefinition::businessCardEnabled).toList();
  }

  Optional<BusinessIntentDefinition> findByIntent(String intent);
}
