package br.com.banco.spider.execution.persistence.model;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import java.time.Instant;
import java.util.Objects;

public record ExecutionControlRecord(
    String executionId,
    String contextId,
    String correlationId,
    String planId,
    String routeCode,
    String routeVersion,
    ExecutionState state,
    long stateVersion,
    TechnicalStatus technicalStatus,
    Instant startedAt,
    Instant completedAt,
    Instant lastUpdatedAt,
    String activeWaitType,
    String retentionClassRef,
    String ownerPrincipalRef) {

  public ExecutionControlRecord {
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(contextId, "contextId");
    Objects.requireNonNull(correlationId, "correlationId");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(lastUpdatedAt, "lastUpdatedAt");
    if (retentionClassRef == null || retentionClassRef.isBlank()) {
      retentionClassRef = "retention:technical-default@1";
    }
  }
}
