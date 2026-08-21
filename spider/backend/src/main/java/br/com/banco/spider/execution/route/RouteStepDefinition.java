package br.com.banco.spider.execution.route;

import java.util.List;
import java.util.Objects;

/**
 * Step de rota linear. {@code dependencies} vazia = step de entrada.
 * Neste incremento: no máximo uma dependência.
 */
public record RouteStepDefinition(
    String stepId,
    String capabilityCode,
    String operationCode,
    String adapterBindingRef,
    String inputContractRef,
    String outputContractRef,
    List<String> dependencies,
    String inputMappingRef,
    String timeoutPolicyRef,
    String retryPolicyRef,
    String resiliencePolicyRef,
    IdempotencyClassification idempotencyClassification,
    RetrySafety retrySafety,
    String evidencePolicyRef,
    String waitPolicyRef) {

  public RouteStepDefinition {
    stepId = require("stepId", stepId);
    capabilityCode = require("capabilityCode", capabilityCode);
    operationCode = require("operationCode", operationCode);
    adapterBindingRef = require("adapterBindingRef", adapterBindingRef);
    inputContractRef = require("inputContractRef", inputContractRef);
    outputContractRef = require("outputContractRef", outputContractRef);
    dependencies = dependencies == null ? List.of() : List.copyOf(dependencies);
    inputMappingRef = require("inputMappingRef", inputMappingRef);
    Objects.requireNonNull(idempotencyClassification, "idempotencyClassification");
    Objects.requireNonNull(retrySafety, "retrySafety");
    timeoutPolicyRef = blankToNull(timeoutPolicyRef);
    retryPolicyRef = blankToNull(retryPolicyRef);
    resiliencePolicyRef = blankToNull(resiliencePolicyRef);
    evidencePolicyRef = blankToNull(evidencePolicyRef);
    waitPolicyRef = blankToNull(waitPolicyRef);
  }

  /** Factory compatível com step único de entrada (PROMPT-002/003). */
  public static RouteStepDefinition entry(
      String stepId,
      String capabilityCode,
      String operationCode,
      String adapterBindingRef,
      String inputContractRef,
      String outputContractRef,
      String timeoutPolicyRef,
      String retryPolicyRef,
      String resiliencePolicyRef,
      IdempotencyClassification idempotencyClassification,
      String evidencePolicyRef) {
    return new RouteStepDefinition(
        stepId,
        capabilityCode,
        operationCode,
        adapterBindingRef,
        inputContractRef,
        outputContractRef,
        List.of(),
        br.com.banco.spider.execution.mapping.StepInputMappingKind.ROOT_REQUEST_CANONICAL_DATA
            .toRef(),
        timeoutPolicyRef,
        retryPolicyRef,
        resiliencePolicyRef,
        idempotencyClassification,
        RetrySafety.SAFE,
        evidencePolicyRef,
        null);
  }

  public static RouteStepDefinition entryAsync(
      String stepId,
      String capabilityCode,
      String operationCode,
      String adapterBindingRef,
      String inputContractRef,
      String outputContractRef,
      String retryPolicyRef,
      IdempotencyClassification idempotencyClassification,
      String waitPolicyRef) {
    return new RouteStepDefinition(
        stepId,
        capabilityCode,
        operationCode,
        adapterBindingRef,
        inputContractRef,
        outputContractRef,
        List.of(),
        br.com.banco.spider.execution.mapping.StepInputMappingKind.ROOT_REQUEST_CANONICAL_DATA
            .toRef(),
        null,
        retryPolicyRef,
        null,
        idempotencyClassification,
        RetrySafety.SAFE,
        null,
        waitPolicyRef);
  }

  public boolean isEntry() {
    return dependencies.isEmpty();
  }

  public boolean admitsAsync() {
    return waitPolicyRef != null;
  }

  private static String require(String name, String value) {
    Objects.requireNonNull(value, name);
    String t = value.trim();
    if (t.isEmpty()) {
      throw new IllegalArgumentException(name + " must not be blank");
    }
    return t;
  }

  private static String blankToNull(String v) {
    if (v == null) {
      return null;
    }
    String t = v.trim();
    return t.isEmpty() ? null : t;
  }
}
