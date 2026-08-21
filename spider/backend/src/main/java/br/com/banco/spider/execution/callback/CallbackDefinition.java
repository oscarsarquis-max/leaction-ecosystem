package br.com.banco.spider.execution.callback;

import java.util.List;
import java.util.Objects;

public record CallbackDefinition(
    String callbackCode,
    String version,
    String bindingRef,
    String callbackContractRef,
    String securityProfileRef,
    String deliveryPolicyRef,
    String projectionRef,
    List<String> allowedOriginatorRefs,
    String maximumDataClassification,
    CallbackDefinitionStatus status,
    String integrityRef,
    CallbackConfirmationMode confirmationMode,
    String statusQueryBindingRef,
    String reconciliationPolicyRef,
    CallbackRedeliverySafety redeliverySafety) {

  public CallbackDefinition {
    Objects.requireNonNull(callbackCode, "callbackCode");
    Objects.requireNonNull(version, "version");
    Objects.requireNonNull(bindingRef, "bindingRef");
    Objects.requireNonNull(callbackContractRef, "callbackContractRef");
    Objects.requireNonNull(securityProfileRef, "securityProfileRef");
    Objects.requireNonNull(deliveryPolicyRef, "deliveryPolicyRef");
    Objects.requireNonNull(projectionRef, "projectionRef");
    Objects.requireNonNull(maximumDataClassification, "maximumDataClassification");
    Objects.requireNonNull(status, "status");
    Objects.requireNonNull(confirmationMode, "confirmationMode");
    Objects.requireNonNull(redeliverySafety, "redeliverySafety");
    allowedOriginatorRefs =
        allowedOriginatorRefs == null ? List.of() : List.copyOf(allowedOriginatorRefs);
    if (status == CallbackDefinitionStatus.PUBLISHED
        && (integrityRef == null || integrityRef.isBlank())) {
      throw new IllegalArgumentException("PUBLISHED callback requires integrityRef");
    }
    if (status == CallbackDefinitionStatus.PUBLISHED) {
      boolean needsQuery =
          confirmationMode == CallbackConfirmationMode.STATUS_QUERY_REQUIRED
              || confirmationMode == CallbackConfirmationMode.STATUS_QUERY_WHEN_UNCERTAIN;
      if (needsQuery) {
        if (statusQueryBindingRef == null || statusQueryBindingRef.isBlank()) {
          throw new IllegalArgumentException("statusQueryBindingRef required for confirmation mode");
        }
        if (reconciliationPolicyRef == null || reconciliationPolicyRef.isBlank()) {
          throw new IllegalArgumentException(
              "reconciliationPolicyRef required for confirmation mode");
        }
      }
    }
  }

  public String exactRef() {
    return callbackCode + "@" + version;
  }

  public boolean isEligible() {
    return status == CallbackDefinitionStatus.PUBLISHED;
  }

  /** Factory compatível: ACK síncrono final, sem query. */
  public static CallbackDefinition published(
      String code,
      String version,
      String bindingRef,
      String contractRef,
      String securityProfileRef,
      String deliveryPolicyRef,
      String projectionRef,
      List<String> originators,
      String maxClassification) {
    return published(
        code,
        version,
        bindingRef,
        contractRef,
        securityProfileRef,
        deliveryPolicyRef,
        projectionRef,
        originators,
        maxClassification,
        CallbackConfirmationMode.SYNCHRONOUS_ACK_IS_FINAL,
        null,
        null,
        CallbackRedeliverySafety.NEVER_AUTOMATIC);
  }

  public static CallbackDefinition published(
      String code,
      String version,
      String bindingRef,
      String contractRef,
      String securityProfileRef,
      String deliveryPolicyRef,
      String projectionRef,
      List<String> originators,
      String maxClassification,
      CallbackConfirmationMode confirmationMode,
      String statusQueryBindingRef,
      String reconciliationPolicyRef,
      CallbackRedeliverySafety redeliverySafety) {
    return new CallbackDefinition(
        code,
        version,
        bindingRef,
        contractRef,
        securityProfileRef,
        deliveryPolicyRef,
        projectionRef,
        originators,
        maxClassification,
        CallbackDefinitionStatus.PUBLISHED,
        "integrity:callback:" + code + "@" + version,
        confirmationMode,
        statusQueryBindingRef,
        reconciliationPolicyRef,
        redeliverySafety);
  }
}
