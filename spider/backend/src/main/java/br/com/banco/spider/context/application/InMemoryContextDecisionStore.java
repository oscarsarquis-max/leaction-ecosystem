package br.com.banco.spider.context.application;

import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/** Read model local do incremento CTX-001; feature default-off e sem papel de SoR do Core. */
public final class InMemoryContextDecisionStore implements ContextDecisionStore {

  private final ConcurrentMap<String, ContextDecisionRecord> byDecision = new ConcurrentHashMap<>();
  private final ConcurrentMap<String, String> decisionByExecution = new ConcurrentHashMap<>();

  @Override
  public void save(ContextDecisionRecord record) {
    byDecision.put(record.decisionId(), record);
    if (record.executionId() != null) {
      decisionByExecution.put(record.executionId(), record.decisionId());
    }
  }

  @Override
  public Optional<ContextDecisionRecord> findByDecisionId(String decisionId) {
    return Optional.ofNullable(byDecision.get(decisionId));
  }

  @Override
  public Optional<ContextDecisionRecord> findByExecutionId(String executionId) {
    String decisionId = decisionByExecution.get(executionId);
    return decisionId == null ? Optional.empty() : findByDecisionId(decisionId);
  }
}
