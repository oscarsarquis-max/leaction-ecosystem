package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import java.util.List;

public interface ExecutionTransitionStorePort {
  void append(ExecutionTransitionRecord transition);

  List<ExecutionTransitionRecord> findByExecutionId(String executionId);

  long nextSequence(String executionId);
}
