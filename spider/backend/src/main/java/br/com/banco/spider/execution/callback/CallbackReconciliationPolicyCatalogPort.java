package br.com.banco.spider.execution.callback;

import java.util.Optional;

public interface CallbackReconciliationPolicyCatalogPort {
  Optional<CallbackReconciliationPolicy> findByExactRef(String exactRef);
}
