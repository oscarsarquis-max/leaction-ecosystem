package br.com.banco.spider.context.capability;

import java.util.List;
import java.util.Optional;

public interface BusinessCapabilityCatalog {
  List<BusinessCapability> list();

  Optional<BusinessCapability> findById(String capabilityId);
}
