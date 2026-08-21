package br.com.banco.spider.execution.domain;

import java.util.Objects;

/** Presente somente após resolução de rota. */
public record ResolutionSummary(String routeId, String routeVersion, String executionPlanRef) {

  public ResolutionSummary {
    Objects.requireNonNull(routeId, "routeId");
    Objects.requireNonNull(routeVersion, "routeVersion");
    routeId = routeId.trim();
    routeVersion = routeVersion.trim();
    if (routeId.isEmpty() || routeVersion.isEmpty()) {
      throw new IllegalArgumentException("routeId and routeVersion must not be blank");
    }
    if (executionPlanRef != null) {
      executionPlanRef = executionPlanRef.trim();
      if (executionPlanRef.isEmpty()) {
        executionPlanRef = null;
      }
    }
  }
}
