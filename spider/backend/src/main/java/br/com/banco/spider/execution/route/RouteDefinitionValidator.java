package br.com.banco.spider.execution.route;

import br.com.banco.spider.canonical.error.CanonicalError;
import br.com.banco.spider.canonical.error.ErrorCategory;
import br.com.banco.spider.canonical.error.ErrorSeverity;
import br.com.banco.spider.execution.mapping.StepInputMappingKind;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.regex.Pattern;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class RouteDefinitionValidator implements RouteDefinitionValidationPort {

  private static final Pattern PHYSICAL =
      Pattern.compile("(?i)(https?://|wss?://|jdbc:|amqp://|kafka://|wsdl|host=|:\\\\|/api/)");

  private final int maxSteps;

  @org.springframework.beans.factory.annotation.Autowired
  public RouteDefinitionValidator(
      @Value("${spider.canonical.route.max-steps:8}") int maxSteps) {
    this.maxSteps = Math.max(1, maxSteps);
  }

  public RouteDefinitionValidator() {
    this(8);
  }

  public int maxSteps() {
    return maxSteps;
  }

  @Override
  public List<CanonicalError> validate(RouteDefinition route) {
    List<CanonicalError> errors = new ArrayList<>();
    if (route == null) {
      errors.add(err("ROUTE_NULL", "Route definition is required", ErrorCategory.CONTRACT));
      return List.copyOf(errors);
    }

    if (route.status() == null) {
      errors.add(err("ROUTE_STATUS_REQUIRED", "status is required", ErrorCategory.CONTRACT));
    }

    if (route.status() != null && route.status().isEligible() && isBlank(route.integrityRef())) {
      errors.add(
          err(
              "ROUTE_INTEGRITY_REQUIRED",
              "integrityRef is required for PUBLISHED routes",
              ErrorCategory.CONTRACT));
    }

    List<RouteStepDefinition> steps = route.steps();
    if (steps == null || steps.isEmpty()) {
      errors.add(err("ROUTE_STEPS_EMPTY", "Route must declare at least one step", ErrorCategory.CONTRACT));
      return List.copyOf(errors);
    }
    if (steps.size() > maxSteps) {
      errors.add(
          err(
              "ROUTE_STEPS_LIMIT",
              "Route exceeds max-steps=" + maxSteps + "; found " + steps.size(),
              ErrorCategory.CONTRACT));
    }

    Set<String> stepIds = new HashSet<>();
    for (RouteStepDefinition step : steps) {
      if (!stepIds.add(step.stepId())) {
        errors.add(err("ROUTE_STEP_ID_DUPLICATE", "Duplicate stepId: " + step.stepId(), ErrorCategory.CONTRACT));
      }
      rejectPhysical(step.adapterBindingRef(), "adapterBindingRef", errors);
      rejectPhysical(step.inputContractRef(), "inputContractRef", errors);
      rejectPhysical(step.outputContractRef(), "outputContractRef", errors);
      rejectPhysical(step.inputMappingRef(), "inputMappingRef", errors);
      rejectPhysical(step.timeoutPolicyRef(), "timeoutPolicyRef", errors);
      rejectPhysical(step.retryPolicyRef(), "retryPolicyRef", errors);
      rejectPhysical(step.resiliencePolicyRef(), "resiliencePolicyRef", errors);
      rejectPhysical(step.evidencePolicyRef(), "evidencePolicyRef", errors);
      rejectPhysical(step.waitPolicyRef(), "waitPolicyRef", errors);
      validateRetrySafety(step, errors);
      try {
        StepInputMappingKind.fromRef(step.inputMappingRef());
      } catch (IllegalArgumentException ex) {
        errors.add(err("ROUTE_MAPPING_INVALID", ex.getMessage(), ErrorCategory.CONTRACT));
      }
    }

    validateLinearChain(route, errors);

    rejectPhysical(route.inputContractRef(), "route.inputContractRef", errors);
    rejectPhysical(route.outputContractRef(), "route.outputContractRef", errors);
    rejectPhysical(route.integrityRef(), "integrityRef", errors);

    return List.copyOf(errors);
  }

  public List<CanonicalError> validateForSelection(RouteDefinition route) {
    List<CanonicalError> errors = new ArrayList<>(validate(route));
    if (route != null && route.status() != null && !route.status().isEligible()) {
      errors.add(
          err(
              "ROUTE_NOT_PUBLISHED",
              "Only PUBLISHED routes are eligible; status=" + route.status(),
              ErrorCategory.RESOLUTION));
    }
    return List.copyOf(errors);
  }

  private void validateLinearChain(RouteDefinition route, List<CanonicalError> errors) {
    List<RouteStepDefinition> steps = route.steps();
    Map<String, RouteStepDefinition> byId = new HashMap<>();
    for (RouteStepDefinition s : steps) {
      byId.put(s.stepId(), s);
    }

    List<RouteStepDefinition> roots = steps.stream().filter(RouteStepDefinition::isEntry).toList();
    if (roots.isEmpty()) {
      errors.add(err("ROUTE_NO_ENTRY", "Exactly one entry step without dependency is required", ErrorCategory.CONTRACT));
      return;
    }
    if (roots.size() > 1) {
      errors.add(
          err(
              "ROUTE_MULTIPLE_ENTRY",
              "Exactly one entry step required; found " + roots.size(),
              ErrorCategory.CONTRACT));
      return;
    }

    RouteStepDefinition entry = roots.getFirst();
    // Target da rota deve coincidir com o step de entrada (não necessariamente com todos).
    if (!route.target().capabilityCode().equals(entry.capabilityCode())
        || !route.target().operationCode().equals(entry.operationCode())) {
      errors.add(
          err(
              "ROUTE_TARGET_MISMATCH",
              "Route target must match entry step capability/operation",
              ErrorCategory.RESOLUTION));
    }

    Map<String, Integer> indegree = new HashMap<>();
    Map<String, List<String>> children = new HashMap<>();
    for (RouteStepDefinition s : steps) {
      indegree.putIfAbsent(s.stepId(), 0);
      children.putIfAbsent(s.stepId(), new ArrayList<>());
    }

    for (RouteStepDefinition s : steps) {
      if (s.dependencies().size() > 1) {
        errors.add(
            err(
                "ROUTE_BRANCH_OR_JOIN",
                "Step " + s.stepId() + " has multiple dependencies; linear chain only",
                ErrorCategory.CONTRACT));
        continue;
      }
      if (!s.isEntry() && s.dependencies().size() != 1) {
        errors.add(
            err(
                "ROUTE_DEPENDENCY_REQUIRED",
                "Non-entry step " + s.stepId() + " must declare exactly one dependency",
                ErrorCategory.CONTRACT));
        continue;
      }
      for (String dep : s.dependencies()) {
        if (!byId.containsKey(dep)) {
          errors.add(
              err(
                  "ROUTE_DEPENDENCY_MISSING",
                  "Dependency " + dep + " not found for step " + s.stepId(),
                  ErrorCategory.CONTRACT));
          continue;
        }
        indegree.merge(s.stepId(), 1, Integer::sum);
        children.computeIfAbsent(dep, k -> new ArrayList<>()).add(s.stepId());
      }
    }

    // Detect branch: node with >1 children
    for (Map.Entry<String, List<String>> e : children.entrySet()) {
      if (e.getValue().size() > 1) {
        errors.add(
            err(
                "ROUTE_BRANCH_FORBIDDEN",
                "Step " + e.getKey() + " has multiple successors; linear chain only",
                ErrorCategory.CONTRACT));
      }
    }

    // Detect join: non-entry with would already be caught; also indegree > 1
    for (Map.Entry<String, Integer> e : indegree.entrySet()) {
      if (e.getValue() > 1) {
        errors.add(
            err(
                "ROUTE_JOIN_FORBIDDEN",
                "Step " + e.getKey() + " has multiple predecessors; linear chain only",
                ErrorCategory.CONTRACT));
      }
    }

    try {
      List<RouteStepDefinition> ordered = LinearRouteOrderer.order(steps);
      if (ordered.size() != steps.size()) {
        errors.add(
            err(
                "ROUTE_UNREACHABLE_OR_CYCLE",
                "Not all steps reachable in a single linear chain",
                ErrorCategory.CONTRACT));
      }
    } catch (LinearRouteOrderer.LinearOrderException ex) {
      errors.add(err(ex.code(), ex.getMessage(), ErrorCategory.CONTRACT));
    }
  }

  private void validateRetrySafety(RouteStepDefinition step, List<CanonicalError> errors) {
    if (step.retrySafety() == RetrySafety.SAFE_WITH_IDEMPOTENCY_KEY
        && step.idempotencyClassification() == IdempotencyClassification.NOT_SUPPORTED) {
      errors.add(
          err(
              "ROUTE_RETRY_SAFETY_INCOMPATIBLE",
              "SAFE_WITH_IDEMPOTENCY_KEY cannot coexist with NOT_SUPPORTED idempotency",
              ErrorCategory.CONTRACT));
    }
  }

  private void rejectPhysical(String value, String field, List<CanonicalError> errors) {
    if (value == null || value.isBlank()) {
      return;
    }
    if (PHYSICAL.matcher(value).find()) {
      errors.add(
          err(
              "ROUTE_PHYSICAL_DETAIL_FORBIDDEN",
              field + " must not contain physical transport detail",
              ErrorCategory.CONTRACT));
    }
    String lower = value.toLowerCase(Locale.ROOT);
    if (lower.contains("{") || lower.contains("\"url\"") || lower.contains("endpoint=")) {
      errors.add(
          err(
              "ROUTE_INLINE_POLICY_FORBIDDEN",
              field + " must be a logical reference, not inline policy/payload",
              ErrorCategory.CONTRACT));
    }
  }

  private static boolean isBlank(String v) {
    return v == null || v.isBlank();
  }

  private static CanonicalError err(String code, String message, ErrorCategory category) {
    return CanonicalError.builder()
        .errorId("err-" + UUID.randomUUID())
        .code(code)
        .category(category)
        .severity(ErrorSeverity.ERROR)
        .message(message)
        .retryable(false)
        .occurredAt(Instant.now())
        .source(new CanonicalError.ErrorSource("route_definition", null, null, null))
        .build();
  }
}
