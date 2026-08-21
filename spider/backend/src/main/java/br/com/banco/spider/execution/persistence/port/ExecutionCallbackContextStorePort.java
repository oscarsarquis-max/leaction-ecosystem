package br.com.banco.spider.execution.persistence.port;

import br.com.banco.spider.execution.callback.ExecutionCallbackContext;
import java.util.Optional;

public interface ExecutionCallbackContextStorePort {
  void insert(ExecutionCallbackContext context);

  Optional<ExecutionCallbackContext> findByExecutionId(String executionId);
}
