package br.com.banco.spider.operational.readmodel;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import java.time.Instant;

public record OperationalExecutionListItem(
    String executionId,
    String correlationRef,
    String routeRef,
    String operationRef,
    ExecutionState state,
    TechnicalStatus technicalStatus,
    String currentStepRef,
    int completedSteps,
    int totalSteps,
    String waitState,
    String callbackState,
    String governanceBundleRef,
    Instant startedAt,
    Instant updatedAt,
    Instant completedAt,
    Long durationMs,
    String safeErrorCode) {}
