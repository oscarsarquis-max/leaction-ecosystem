package br.com.banco.spider.execution.callback;

import java.time.Instant;
import java.util.Objects;

public record ExecutionCallbackContext(
    String executionId,
    String callbackDefinitionRef,
    String bindingRef,
    String callbackContractRef,
    String securityProfileRef,
    String deliveryPolicyRef,
    String projectionRef,
    String authorizedOriginatorRef,
    String integrityRef,
    Instant fixedAt,
    CallbackConfirmationMode confirmationMode,
    String statusQueryBindingRef,
    String reconciliationPolicyRef,
    CallbackRedeliverySafety redeliverySafety,
    String deliveryKeyHash) {

  public ExecutionCallbackContext {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(callbackDefinitionRef, "callbackDefinitionRef");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(callbackContractRef, "callbackContractRef");
    Objects.requireNonNull(securityProfileRef, "securityProfileRef");
    Objects.requireNonNull(deliveryPolicyRef, "deliveryPolicyRef");
    Objects.requireNonNull(projectionRef, "projectionRef");
    Objects.requireNonNull(authorizedOriginatorRef, "authorizedOriginatorRef");
    Objects.requireNonNull(integrityRef, "integrityRef");
    Objects.requireNonNull(fixedAt, "fixedAt");
    Objects.requireNonNull(confirmationMode, "confirmationMode");
    Objects.requireNonNull(redeliverySafety, "redeliverySafety");
    Objects.requireNonNull(deliveryKeyHash, "deliveryKeyHash");
  }
}
