package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.callback.ExecutionCallbackContext;
import br.com.banco.spider.execution.persistence.port.ExecutionCallbackContextStorePort;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionCallbackContextStore implements ExecutionCallbackContextStorePort {

  private final Map<String, ExecutionCallbackContext> byExecution = new ConcurrentHashMap<>();

  @Override
  public void insert(ExecutionCallbackContext context) {
    if (byExecution.putIfAbsent(context.executionId(), context) != null) {
      throw new IllegalStateException("Callback context already exists for " + context.executionId());
    }
  }

  @Override
  public Optional<ExecutionCallbackContext> findByExecutionId(String executionId) {
    return Optional.ofNullable(byExecution.get(executionId));
  }

  public void clear() {
    byExecution.clear();
  }
}
