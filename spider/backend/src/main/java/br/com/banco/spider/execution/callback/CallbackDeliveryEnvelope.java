package br.com.banco.spider.execution.callback;

import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.security.integrity.IntegrityProof;
import com.fasterxml.jackson.databind.JsonNode;
import java.time.Instant;
import java.util.Objects;

public record CallbackDeliveryEnvelope(
    String callbackContractVersion,
    String deliveryId,
    String logicalCallbackId,
    String callbackDefinitionRef,
    String executionId,
    String correlationId,
    int attemptNumber,
    String logicalIdempotencyKey,
    Instant dispatchedAt,
    TraceDescriptor trace,
    JsonNode payloadProjection,
    IntegrityProof integrityProof) {

  public CallbackDeliveryEnvelope {
    Objects.requireNonNull(callbackContractVersion, "callbackContractVersion");
    Objects.requireNonNull(deliveryId, "deliveryId");
    Objects.requireNonNull(logicalCallbackId, "logicalCallbackId");
    Objects.requireNonNull(callbackDefinitionRef, "callbackDefinitionRef");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(correlationId, "correlationId");
    Objects.requireNonNull(logicalIdempotencyKey, "logicalIdempotencyKey");
    Objects.requireNonNull(dispatchedAt, "dispatchedAt");
    Objects.requireNonNull(payloadProjection, "payloadProjection");
  }

  /** Compatível com callers sem proof (PROMPT-007/008). */
  public CallbackDeliveryEnvelope(
      String callbackContractVersion,
      String deliveryId,
      String logicalCallbackId,
      String callbackDefinitionRef,
      String executionId,
      String correlationId,
      int attemptNumber,
      String logicalIdempotencyKey,
      Instant dispatchedAt,
      TraceDescriptor trace,
      JsonNode payloadProjection) {
    this(
        callbackContractVersion,
        deliveryId,
        logicalCallbackId,
        callbackDefinitionRef,
        executionId,
        correlationId,
        attemptNumber,
        logicalIdempotencyKey,
        dispatchedAt,
        trace,
        payloadProjection,
        null);
  }
}
