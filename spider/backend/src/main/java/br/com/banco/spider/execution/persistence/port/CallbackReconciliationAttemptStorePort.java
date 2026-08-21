package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.callback.CallbackReconciliationAttempt;
import java.util.List;
import java.util.Optional;

public interface CallbackReconciliationAttemptStorePort {
  void insert(CallbackReconciliationAttempt attempt);

  Optional<CallbackReconciliationAttempt> findByReconciliationAndNumber(
      String reconciliationId, int attemptNumber);

  List<CallbackReconciliationAttempt> findByReconciliationId(String reconciliationId);

  int countByReconciliationId(String reconciliationId);
}
