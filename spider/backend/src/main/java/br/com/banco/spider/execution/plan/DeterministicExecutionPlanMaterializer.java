package br.com.banco.spider.execution.plan;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.route.LinearRouteOrderer;
import br.com.banco.spider.execution.route.RouteDefinition;
import br.com.banco.spider.execution.route.RouteDefinitionValidator;
import br.com.banco.spider.execution.route.RouteResolution;
import br.com.banco.spider.execution.route.RouteStepDefinition;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Instant;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

@Service
public class DeterministicExecutionPlanMaterializer implements ExecutionPlanMaterializerPort {

  private static final Logger log = LoggerFactory.getLogger(DeterministicExecutionPlanMaterializer.class);

  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final IntegrityDigestPort digest;
  private final RouteDefinitionValidator validator;

  @org.springframework.beans.factory.annotation.Autowired
  public DeterministicExecutionPlanMaterializer(
      IdentifierGenerator ids,
      SpiderClock clock,
      IntegrityDigestPort digest,
      RouteDefinitionValidator validator) {
    this.ids = ids;
    this.clock = clock;
    this.digest = digest;
    this.validator = validator;
  }

  /** Compatível com testes que não injetam validator. */
  public DeterministicExecutionPlanMaterializer(
      IdentifierGenerator ids, SpiderClock clock, IntegrityDigestPort digest) {
    this(ids, clock, digest, new RouteDefinitionValidator());
  }

  @Override
  public ExecutionPlanMaterialization materialize(
      CanonicalExecutionRequest request, RouteResolution resolution) {
    List<CanonicalError> errors = new ArrayList<>();
    if (resolution == null || !resolution.selected() || resolution.selectedRoute() == null) {
      errors.add(error("PLAN_ROUTE_REQUIRED", "Successful route resolution is required"));
      return ExecutionPlanMaterialization.failed(errors);
    }

    RouteDefinition route = resolution.selectedRoute();
    List<CanonicalError> routeErrors = validator.validate(route);
    if (!routeErrors.isEmpty()) {
      return ExecutionPlanMaterialization.failed(routeErrors);
    }

    List<RouteStepDefinition> ordered;
    try {
      ordered = LinearRouteOrderer.order(route.steps());
    } catch (LinearRouteOrderer.LinearOrderException ex) {
      errors.add(error(ex.code(), ex.getMessage()));
      return ExecutionPlanMaterialization.failed(errors);
    }

    Instant createdAt = clock.now();
    String planId = ids.nextId("plan");
    String executionId = request.execution().executionId();

    List<ExecutionPlanNode> nodes = new ArrayList<>();
    Map<String, String> contracts = new LinkedHashMap<>();
    contracts.put("input", route.inputContractRef());
    contracts.put("output", route.outputContractRef());

    int pos = 0;
    for (RouteStepDefinition step : ordered) {
      if (isBlank(step.adapterBindingRef())
          || isBlank(step.inputContractRef())
          || isBlank(step.outputContractRef())
          || isBlank(step.inputMappingRef())) {
        errors.add(error("PLAN_REF_MISSING", "Binding/contract/mapping refs required: " + step.stepId()));
        return ExecutionPlanMaterialization.failed(errors);
      }
      Map<String, String> policies = new LinkedHashMap<>();
      if (step.timeoutPolicyRef() != null) {
        policies.put("timeout", step.timeoutPolicyRef());
      }
      if (step.retryPolicyRef() != null) {
        policies.put("retry", step.retryPolicyRef());
      }
      if (step.resiliencePolicyRef() != null) {
        policies.put("resilience", step.resiliencePolicyRef());
      }
      if (step.evidencePolicyRef() != null) {
        policies.put("evidence", step.evidencePolicyRef());
      }
      if (step.waitPolicyRef() != null) {
        policies.put("wait", step.waitPolicyRef());
      }
      nodes.add(
          new ExecutionPlanNode(
              step.stepId(),
              pos,
              step.capabilityCode(),
              step.operationCode(),
              step.adapterBindingRef(),
              step.inputContractRef(),
              step.outputContractRef(),
              step.dependencies(),
              step.inputMappingRef(),
              policies,
              step.idempotencyClassification(),
              step.retrySafety(),
              step.waitPolicyRef(),
              List.of("SUCCEEDED", "FAILED", "TIMED_OUT", "WAITING_EXTERNAL", "SKIPPED")));
      contracts.put("step." + step.stepId() + ".input", step.inputContractRef());
      contracts.put("step." + step.stepId() + ".output", step.outputContractRef());
      pos++;
    }

    ExecutionPlan draft =
        new ExecutionPlan(
            planId,
            executionId,
            createdAt,
            new RouteRef(route.routeCode(), route.version()),
            route.journeyRef(),
            contracts,
            nodes,
            List.of("SUCCEEDED", "FAILED", "TIMED_OUT", "WAITING_EXTERNAL", "REJECTED"),
            "pending",
            PlanStatus.MATERIALIZED);

    String integrity = digest.digest(draft.canonicalRepresentation());
    ExecutionPlan plan =
        new ExecutionPlan(
            draft.planId(),
            draft.executionId(),
            draft.createdAt(),
            draft.routeRef(),
            draft.journeyRef(),
            draft.contractRefs(),
            draft.nodes(),
            draft.terminalDefinitions(),
            integrity,
            PlanStatus.MATERIALIZED);

    log.info(
        "event=plan_materialized planId={} executionId={} routeCode={} routeVersion={} steps={} integrityRef={}",
        plan.planId(),
        plan.executionId(),
        plan.routeRef().routeCode(),
        plan.routeRef().routeVersion(),
        plan.nodes().size(),
        plan.integrityRef());

    return ExecutionPlanMaterialization.ok(plan);
  }

  private static boolean isBlank(String v) {
    return v == null || v.isBlank();
  }

  private static CanonicalError error(String code, String message) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(ErrorCategory.INTERNAL)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("plan_materializer", null, null, null))
        .build();
  }
}
