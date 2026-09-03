package br.com.banco.spider.context.application;

import java.util.Optional;

public interface ContextDecisionStore {
  void save(ContextDecisionRecord record);

  Optional<ContextDecisionRecord> findByDecisionId(String decisionId);

  Optional<ContextDecisionRecord> findByExecutionId(String executionId);
}
