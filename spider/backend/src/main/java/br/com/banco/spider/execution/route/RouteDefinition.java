package br.com.banco.spider.execution.route;

import java.util.List;
import java.util.Objects;

/**
 * Route Definition imutável (SPIDER-ARCH-005). Neste incremento: exatamente um step linear.
 */
public record RouteDefinition(
    String routeCode,
    String version,
    String journeyRef,
    RouteStatus status,
    String inputContractRef,
    String outputContractRef,
    RouteTarget target,
    int priority,
    List<RouteStepDefinition> steps,
    String integrityRef) {

  public RouteDefinition {
    routeCode = require("routeCode", routeCode);
    version = require("version", version);
    journeyRef = require("journeyRef", journeyRef);
    Objects.requireNonNull(status, "status");
    inputContractRef = require("inputContractRef", inputContractRef);
    outputContractRef = require("outputContractRef", outputContractRef);
    Objects.requireNonNull(target, "target");
    steps = steps == null ? List.of() : List.copyOf(steps);
    integrityRef = blankToNull(integrityRef);
  }

  public RouteStepDefinition singleStep() {
    if (steps.size() != 1) {
      throw new IllegalStateException("Route must have exactly one step in this increment");
    }
    return steps.getFirst();
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
