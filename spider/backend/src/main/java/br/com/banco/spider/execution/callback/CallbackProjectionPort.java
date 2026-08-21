package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import com.fasterxml.jackson.databind.JsonNode;
import reactor.core.publisher.Mono;

public interface CallbackProjectionPort {
  Mono<JsonNode> project(
      CallbackProjectionKind kind,
      CanonicalExecutionResult result,
      String maximumDataClassification);
}
