package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import br.com.banco.spider.execution.persistence.port.ExecutionResultStorePort;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryExecutionResultStore implements ExecutionResultStorePort {

  private final Map<String, PersistedExecutionResult> byRef = new ConcurrentHashMap<>();
  private final Map<String, String> executionToResult = new ConcurrentHashMap<>();

  @Override
  public void insert(PersistedExecutionResult result) {
    if (byRef.putIfAbsent(result.resultRef(), result) != null) {
      throw new IllegalStateException("Result already exists: " + result.resultRef());
    }
    if (executionToResult.putIfAbsent(result.executionId(), result.resultRef()) != null) {
      byRef.remove(result.resultRef());
      throw new IllegalStateException("Result already exists for execution: " + result.executionId());
    }
  }

  @Override
  public synchronized void replaceByExecutionId(PersistedExecutionResult result) {
    String oldRef = executionToResult.get(result.executionId());
    if (oldRef != null) {
      byRef.remove(oldRef);
    }
    byRef.put(result.resultRef(), result);
    executionToResult.put(result.executionId(), result.resultRef());
  }

  @Override
  public Optional<PersistedExecutionResult> findByResultRef(String resultRef) {
    return Optional.ofNullable(byRef.get(resultRef));
  }

  @Override
  public Optional<PersistedExecutionResult> findByExecutionId(String executionId) {
    String ref = executionToResult.get(executionId);
    return ref == null ? Optional.empty() : findByResultRef(ref);
  }

  public void clear() {
    byRef.clear();
    executionToResult.clear();
  }
}
