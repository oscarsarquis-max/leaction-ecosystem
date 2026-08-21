package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import java.util.Optional;

public interface ExecutionResultStorePort {
  void insert(PersistedExecutionResult result);

  /** Substitui resultado PENDING/WAITING por resultado terminal na retomada. */
  void replaceByExecutionId(PersistedExecutionResult result);

  Optional<PersistedExecutionResult> findByResultRef(String resultRef);

  Optional<PersistedExecutionResult> findByExecutionId(String executionId);
}
