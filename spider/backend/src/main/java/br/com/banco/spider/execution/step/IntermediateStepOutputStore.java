package br.com.banco.spider.execution.step;

import com.fasterxml.jackson.databind.JsonNode;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/** Outputs intermediários técnicos em memória (não cadastro de negócio). */
@Component
public class IntermediateStepOutputStore {

  private final Map<String, JsonNode> byKey = new ConcurrentHashMap<>();

  private static String key(String executionId, String stepId) {
    return executionId + "|" + stepId;
  }

  public void put(String executionId, String stepId, JsonNode data) {
    byKey.put(key(executionId, stepId), data == null ? null : data.deepCopy());
  }

  public Optional<JsonNode> get(String executionId, String stepId) {
    return Optional.ofNullable(byKey.get(key(executionId, stepId)));
  }

  public void clearExecution(String executionId) {
    byKey.keySet().removeIf(k -> k.startsWith(executionId + "|"));
  }
}
