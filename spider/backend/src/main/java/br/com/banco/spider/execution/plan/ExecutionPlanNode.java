package br.com.banco.spider.execution.plan;

import br.com.banco.spider.execution.route.IdempotencyClassification;
import br.com.banco.spider.execution.route.RetrySafety;
import java.util.List;
import java.util.Map;
import java.util.Objects;

public record ExecutionPlanNode(
    String stepId,
    int orderedPosition,
    String capabilityCode,
    String operationCode,
    String adapterBindingRef,
    String inputContractRef,
    String outputContractRef,
    List<String> dependencies,
    String inputMappingRef,
    Map<String, String> effectivePolicyRefs,
    IdempotencyClassification idempotencyClassification,
    RetrySafety retrySafety,
    String waitPolicyRef,
    List<String> allowedTransitions) {

  public ExecutionPlanNode {
    Objects.requireNonNull(stepId, "stepId");
    Objects.requireNonNull(capabilityCode, "capabilityCode");
    Objects.requireNonNull(operationCode, "operationCode");
    Objects.requireNonNull(adapterBindingRef, "adapterBindingRef");
    Objects.requireNonNull(inputContractRef, "inputContractRef");
    Objects.requireNonNull(outputContractRef, "outputContractRef");
    Objects.requireNonNull(inputMappingRef, "inputMappingRef");
    Objects.requireNonNull(idempotencyClassification, "idempotencyClassification");
    Objects.requireNonNull(retrySafety, "retrySafety");
    dependencies = dependencies == null ? List.of() : List.copyOf(dependencies);
    effectivePolicyRefs =
        effectivePolicyRefs == null ? Map.of() : Map.copyOf(effectivePolicyRefs);
    allowedTransitions =
        allowedTransitions == null ? List.of() : List.copyOf(allowedTransitions);
  }
}
