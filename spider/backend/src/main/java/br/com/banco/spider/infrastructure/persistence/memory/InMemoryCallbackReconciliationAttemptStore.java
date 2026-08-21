package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.callback.CallbackReconciliationAttempt;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationAttemptStorePort;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryCallbackReconciliationAttemptStore
    implements CallbackReconciliationAttemptStorePort {

  private final Map<String, CallbackReconciliationAttempt> byId = new ConcurrentHashMap<>();
  private final Map<String, List<String>> byReconciliation = new ConcurrentHashMap<>();

  @Override
  public synchronized void insert(CallbackReconciliationAttempt attempt) {
    String key = attempt.reconciliationId() + "#" + attempt.attemptNumber();
    if (byId.values().stream()
        .anyMatch(
            a ->
                a.reconciliationId().equals(attempt.reconciliationId())
                    && a.attemptNumber() == attempt.attemptNumber())) {
      throw new IllegalStateException("Duplicate reconciliation attempt number");
    }
    byId.put(attempt.reconciliationAttemptId(), attempt);
    byReconciliation
        .computeIfAbsent(attempt.reconciliationId(), k -> new ArrayList<>())
        .add(attempt.reconciliationAttemptId());
  }

  @Override
  public Optional<CallbackReconciliationAttempt> findByReconciliationAndNumber(
      String reconciliationId, int attemptNumber) {
    return findByReconciliationId(reconciliationId).stream()
        .filter(a -> a.attemptNumber() == attemptNumber)
        .findFirst();
  }

  @Override
  public List<CallbackReconciliationAttempt> findByReconciliationId(String reconciliationId) {
    List<String> ids = byReconciliation.getOrDefault(reconciliationId, List.of());
    List<CallbackReconciliationAttempt> list = new ArrayList<>();
    for (String id : ids) {
      CallbackReconciliationAttempt a = byId.get(id);
      if (a != null) {
        list.add(a);
      }
    }
    return List.copyOf(list);
  }

  @Override
  public int countByReconciliationId(String reconciliationId) {
    return findByReconciliationId(reconciliationId).size();
  }

  public void clear() {
    byId.clear();
    byReconciliation.clear();
  }
}
