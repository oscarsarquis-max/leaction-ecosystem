package br.com.banco.spider.execution.route;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Ordenação topológica restrita a cadeia linear.
 * Resultado independente da ordem de inserção na collection.
 */
public final class LinearRouteOrderer {

  private LinearRouteOrderer() {}

  public static List<RouteStepDefinition> order(List<RouteStepDefinition> steps) {
    if (steps == null || steps.isEmpty()) {
      throw new LinearOrderException("ROUTE_STEPS_EMPTY", "No steps to order");
    }
    Map<String, RouteStepDefinition> byId = new HashMap<>();
    Map<String, String> predecessor = new HashMap<>();
    Map<String, String> successor = new HashMap<>();

    for (RouteStepDefinition s : steps) {
      if (byId.put(s.stepId(), s) != null) {
        throw new LinearOrderException("ROUTE_STEP_ID_DUPLICATE", "Duplicate stepId " + s.stepId());
      }
    }

    List<RouteStepDefinition> roots = new ArrayList<>();
    for (RouteStepDefinition s : steps) {
      if (s.dependencies().size() > 1) {
        throw new LinearOrderException(
            "ROUTE_BRANCH_OR_JOIN", "Multiple dependencies on " + s.stepId());
      }
      if (s.isEntry()) {
        roots.add(s);
      } else {
        String dep = s.dependencies().getFirst();
        if (!byId.containsKey(dep)) {
          throw new LinearOrderException(
              "ROUTE_DEPENDENCY_MISSING", "Missing dependency " + dep);
        }
        if (predecessor.put(s.stepId(), dep) != null) {
          throw new LinearOrderException("ROUTE_JOIN_FORBIDDEN", "Join at " + s.stepId());
        }
        if (successor.put(dep, s.stepId()) != null) {
          throw new LinearOrderException("ROUTE_BRANCH_FORBIDDEN", "Branch at " + dep);
        }
      }
    }
    if (roots.size() != 1) {
      throw new LinearOrderException(
          "ROUTE_ENTRY_INVALID", "Exactly one entry step required; found " + roots.size());
    }

    List<RouteStepDefinition> ordered = new ArrayList<>();
    Set<String> seen = new HashSet<>();
    RouteStepDefinition current = roots.getFirst();
    while (current != null) {
      if (!seen.add(current.stepId())) {
        throw new LinearOrderException("ROUTE_CYCLE", "Cycle detected at " + current.stepId());
      }
      ordered.add(current);
      String nextId = successor.get(current.stepId());
      current = nextId == null ? null : byId.get(nextId);
    }

    if (ordered.size() != steps.size()) {
      throw new LinearOrderException(
          "ROUTE_UNREACHABLE_OR_CYCLE", "Unreachable steps or incomplete linear chain");
    }
    return List.copyOf(ordered);
  }

  public static final class LinearOrderException extends RuntimeException {
    private final String code;

    public LinearOrderException(String code, String message) {
      super(message);
      this.code = code;
    }

    public String code() {
      return code;
    }
  }
}
