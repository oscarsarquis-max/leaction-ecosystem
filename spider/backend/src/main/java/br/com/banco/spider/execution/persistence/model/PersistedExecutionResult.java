package br.com.banco.spider.execution.persistence.model;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import java.time.Instant;
import java.util.Objects;

public record PersistedExecutionResult(
    String resultRef,
    String executionId,
    String contractVersion,
    ExecutionState state,
    TechnicalStatus technicalStatus,
    String resultRepresentation,
    String contentDigest,
    Instant createdAt,
    Instant expiresAt) {

  public PersistedExecutionResult {
    Objects.requireNonNull(resultRef, "resultRef");
    Objects.requireNonNull(executionId, "executionId");
    Objects.requireNonNull(contractVersion, "contractVersion");
    Objects.requireNonNull(state, "state");
    Objects.requireNonNull(technicalStatus, "technicalStatus");
    Objects.requireNonNull(resultRepresentation, "resultRepresentation");
    Objects.requireNonNull(contentDigest, "contentDigest");
    Objects.requireNonNull(createdAt, "createdAt");
    Objects.requireNonNull(expiresAt, "expiresAt");
  }
}
