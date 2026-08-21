package br.com.banco.spider.execution.callback;

import java.util.List;
import java.util.Optional;

public interface CallbackDeliveryPolicyCatalogPort {
  Optional<CallbackDeliveryPolicy> findByExactRef(String exactRef);
}
