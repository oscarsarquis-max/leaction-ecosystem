package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.canonical.error.CanonicalError;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ArrayNode;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.util.List;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

@Component
public class DefaultCallbackProjectionAdapter implements CallbackProjectionPort {

  private final ObjectMapper mapper;

  public DefaultCallbackProjectionAdapter(ObjectMapper mapper) {
    this.mapper = mapper;
  }

  @Override
  public Mono<JsonNode> project(
      CallbackProjectionKind kind,
      CanonicalExecutionResult result,
      String maximumDataClassification) {
    return Mono.fromCallable(
        () ->
            switch (kind) {
              case MINIMAL_STATUS_V1 -> minimal(result);
              case CANONICAL_RESULT_V1 -> full(result, maximumDataClassification);
            });
  }

  private JsonNode minimal(CanonicalExecutionResult result) {
    ObjectNode root = mapper.createObjectNode();
    root.put("contractVersion", result.contract().contractVersion());
    root.put("executionId", result.execution().executionId());
    if (result.contextRef() != null) {
      root.put("contextId", result.contextRef().contextId());
    }
    root.put("correlationId", result.trace().correlationId());
    root.put("state", result.state().name());
    if (result.outcome() != null && result.outcome().technicalStatus() != null) {
      root.put("technicalStatus", result.outcome().technicalStatus().name());
    }
    if (result.execution().completedAt() != null) {
      root.put("completedAt", result.execution().completedAt().toString());
    }
    ArrayNode errors = root.putArray("errors");
    for (CanonicalError e : result.errors() == null ? List.<CanonicalError>of() : result.errors()) {
      ObjectNode err = errors.addObject();
      err.put("code", e.code());
      err.put("category", e.category().name());
    }
    ArrayNode ev = root.putArray("evidenceRefs");
    if (result.evidenceRefs() != null) {
      result.evidenceRefs().forEach(r -> ev.add(r.evidenceId()));
    }
    return root;
  }

  private JsonNode full(CanonicalExecutionResult result, String maxClass) {
    if (maxClass == null || maxClass.isBlank() || "PUBLIC".equalsIgnoreCase(maxClass)) {
      throw new IllegalArgumentException("CANONICAL_RESULT_V1 requires adequate classification");
    }
    ObjectNode root = (ObjectNode) minimal(result);
    if (result.outcome() != null) {
      ObjectNode outcome = root.putObject("outcome");
      if (result.outcome().technicalStatus() != null) {
        outcome.put("technicalStatus", result.outcome().technicalStatus().name());
      }
      if (result.outcome().businessOutcome() != null) {
        outcome.set("businessOutcome", result.outcome().businessOutcome());
      }
      if (result.outcome().canonicalData() != null) {
        outcome.set("canonicalData", result.outcome().canonicalData());
      }
    }
    return root;
  }
}
