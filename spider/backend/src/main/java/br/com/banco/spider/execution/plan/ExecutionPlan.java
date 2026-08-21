package br.com.banco.spider.execution.plan;

import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Objects;

/** Execution Plan imutável com versões fixadas. */
public record ExecutionPlan(
    String planId,
    String executionId,
    Instant createdAt,
    RouteRef routeRef,
    String journeyRef,
    Map<String, String> contractRefs,
    List<ExecutionPlanNode> nodes,
    List<String> terminalDefinitions,
    String integrityRef,
    PlanStatus status) {

  public ExecutionPlan {
    Objects.requireNonNull(planId, "planId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(routeRef, "routeRef");
    Objects.requireNonNull(journeyRef, "journeyRef");
    Objects.requireNonNull(status, "status");
    contractRefs = contractRefs == null ? Map.of() : Map.copyOf(contractRefs);
    nodes = nodes == null ? List.of() : List.copyOf(nodes);
    terminalDefinitions =
        terminalDefinitions == null ? List.of() : List.copyOf(terminalDefinitions);
    Objects.requireNonNull(integrityRef, "integrityRef");
  }

  public ExecutionPlanNode singleNode() {
    if (nodes.size() != 1) {
      throw new IllegalStateException("Plan does not have exactly one node");
    }
    return nodes.getFirst();
  }

  public List<ExecutionPlanNode> orderedNodes() {
    return nodes;
  }

  /** Representação canônica estável para digest. */
  public String canonicalRepresentation() {
    StringBuilder sb = new StringBuilder();
    sb.append("planId=").append(planId).append('\n');
    sb.append("executionId=").append(executionId).append('\n');
    sb.append("createdAt=").append(createdAt).append('\n');
    sb.append("route=")
        .append(routeRef.routeCode())
        .append('@')
        .append(routeRef.routeVersion())
        .append('\n');
    sb.append("journeyRef=").append(journeyRef).append('\n');
    contractRefs.entrySet().stream()
        .sorted(Map.Entry.comparingByKey())
        .forEach(e -> sb.append("contract.").append(e.getKey()).append('=').append(e.getValue()).append('\n'));
    for (ExecutionPlanNode node : nodes) {
      sb.append("node.")
          .append(node.orderedPosition())
          .append('|')
          .append(node.stepId())
          .append('|')
          .append(node.capabilityCode())
          .append('|')
          .append(node.operationCode())
          .append('|')
          .append(node.adapterBindingRef())
          .append('|')
          .append(node.inputContractRef())
          .append('|')
          .append(node.outputContractRef())
          .append('|')
          .append(node.inputMappingRef())
          .append('|')
          .append(node.idempotencyClassification())
          .append('|')
          .append(node.retrySafety())
          .append('|')
          .append(String.join(",", node.dependencies()))
          .append('\n');
      node.effectivePolicyRefs().entrySet().stream()
          .sorted(Map.Entry.comparingByKey())
          .forEach(
              e ->
                  sb.append("policy.")
                      .append(node.stepId())
                      .append('.')
                      .append(e.getKey())
                      .append('=')
                      .append(e.getValue())
                      .append('\n'));
    }
    terminalDefinitions.stream().sorted().forEach(t -> sb.append("terminal=").append(t).append('\n'));
    sb.append("status=").append(status).append('\n');
    return sb.toString();
  }
}
