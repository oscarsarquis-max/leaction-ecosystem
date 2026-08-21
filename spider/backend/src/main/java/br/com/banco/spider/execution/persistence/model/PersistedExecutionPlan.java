package br.com.banco.spider.execution.persistence.model;

import java.time.Instant;
import java.util.Objects;

public record PersistedExecutionPlan(
    String planId,
    String executionId,
    String routeCode,
    String routeVersion,
    String journeyRef,
    Instant createdAt,
    String integrityRef,
    String schemaVersion,
    String canonicalPlanRepresentation) {

  public PersistedExecutionPlan {
    Objects.requireNonNull(planId, "planId");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(routeCode, "routeCode");
    Objects.requireNonNull(routeVersion, "routeVersion");
    Objects.requireNonNull(journeyRef, "journeyRef");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(integrityRef, "integrityRef");
    Objects.requireNonNull(canonicalPlanRepresentation, "canonicalPlanRepresentation");
    if (schemaVersion == null || schemaVersion.isBlank()) {
      schemaVersion = "1.0";
    }
  }
}
