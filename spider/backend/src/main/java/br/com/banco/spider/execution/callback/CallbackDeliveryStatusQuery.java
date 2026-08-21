package br.com.banco.spider.execution.callback;

import br.com.banco.spider.security.integrity.IntegrityProof;
import java.time.Instant;
import java.util.Objects;

public record CallbackDeliveryStatusQuery(
    String executionId,
    String callbackDefinitionRef,
    String deliveryKey,
    String externalDeliveryRef,
    String contractRef,
    String bindingRef,
    String securityProfileRef,
    int queryAttemptNumber,
    Instant queryDeadline,
    String correlationId,
    String traceparent,
    IntegrityProof integrityProof) {

  public CallbackDeliveryStatusQuery {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(callbackDefinitionRef, "callbackDefinitionRef");
    Objects.requireNonNull(deliveryKey, "deliveryKey");
    Objects.requireNonNull(contractRef, "contractRef");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(securityProfileRef, "securityProfileRef");
    Objects.requireNonNull(queryDeadline, "queryDeadline");
    Objects.requireNonNull(correlationId, "correlationId");
  }

  public CallbackDeliveryStatusQuery(
      String executionId,
      String callbackDefinitionRef,
      String deliveryKey,
      String externalDeliveryRef,
      String contractRef,
      String bindingRef,
      String securityProfileRef,
      int queryAttemptNumber,
      Instant queryDeadline,
      String correlationId,
      String traceparent) {
    this(
        executionId,
        callbackDefinitionRef,
        deliveryKey,
        externalDeliveryRef,
        contractRef,
        bindingRef,
        securityProfileRef,
        queryAttemptNumber,
        queryDeadline,
        correlationId,
        traceparent,
        null);
  }
}
