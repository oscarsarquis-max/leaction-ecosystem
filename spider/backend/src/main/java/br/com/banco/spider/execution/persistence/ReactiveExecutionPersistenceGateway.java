package br.com.banco.spider.execution.persistence;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyReservationResult;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyScope;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import br.com.banco.spider.execution.plan.ExecutionPlan;
import br.com.banco.spider.infrastructure.persistence.BlockingPersistenceSupport;
import java.util.Optional;
import org.springframework.stereotype.Component;
import reactor.core.publisher.Mono;

/** Facade reativa — isola JPA/bloqueante da event loop WebFlux. */
@Component
public class ReactiveExecutionPersistenceGateway {

  private final ExecutionPersistenceCoordinator coordinator;
  private final BlockingPersistenceSupport blocking;

  public ReactiveExecutionPersistenceGateway(
      ExecutionPersistenceCoordinator coordinator, BlockingPersistenceSupport blocking) {
    this.coordinator = coordinator;
    this.blocking = blocking;
  }

  public Mono<IdempotencyReservationResult> reserveOrCreate(
      CanonicalExecutionRequest request,
      IdempotencyScope scope,
      String rawKey,
      boolean createWithoutKey) {
    return reserveOrCreate(request, scope, rawKey, createWithoutKey, null);
  }

  public Mono<IdempotencyReservationResult> reserveOrCreate(
      CanonicalExecutionRequest request,
      IdempotencyScope scope,
      String rawKey,
      boolean createWithoutKey,
      String ownerPrincipalRef) {
    return blocking.defer(
        () ->
            coordinator.reserveOrCreate(
                request, scope, rawKey, createWithoutKey, ownerPrincipalRef));
  }

  public Mono<ExecutionControlRecord> transition(
      String executionId,
      ExecutionState expectedState,
      long expectedVersion,
      ExecutionState newState,
      String reasonCode,
      TechnicalStatus technicalStatus,
      String planId,
      String routeCode,
      String routeVersion,
      String activeWaitType) {
    return blocking.defer(
        () ->
            coordinator.transition(
                executionId,
                expectedState,
                expectedVersion,
                newState,
                reasonCode,
                technicalStatus,
                planId,
                routeCode,
                routeVersion,
                activeWaitType));
  }

  public Mono<ExecutionControlRecord> persistPlan(ExecutionPlan plan, long expectedVersion) {
    return blocking.defer(() -> coordinator.persistPlan(plan, expectedVersion));
  }

  public Mono<PersistedExecutionResult> persistTerminalResult(
      CanonicalExecutionResult result,
      IdempotencyRecordState idempotencyState,
      String scopeHash,
      String keyHash) {
    return blocking.defer(
        () -> coordinator.persistTerminalResult(result, idempotencyState, scopeHash, keyHash));
  }

  public Mono<Void> markIdempotencyInProgress(String scopeHash, String keyHash) {
    return blocking.defer(
        () -> {
          coordinator.markIdempotencyInProgress(scopeHash, keyHash);
          return null;
        });
  }

  public Mono<Optional<PersistedExecutionResult>> findResult(String resultRef) {
    return blocking.defer(() -> coordinator.findResult(resultRef));
  }

  public Mono<Optional<PersistedExecutionResult>> findResultByExecutionId(String executionId) {
    return blocking.defer(() -> coordinator.findResultByExecutionId(executionId));
  }

  public Mono<Optional<ExecutionControlRecord>> findControl(String executionId) {
    return blocking.defer(() -> coordinator.findControl(executionId));
  }

  public Mono<Optional<PersistedExecutionPlan>> findPlan(String executionId) {
    return blocking.defer(() -> coordinator.findPlan(executionId));
  }

  public Mono<CanonicalExecutionResult> loadResult(PersistedExecutionResult persisted) {
    return blocking.defer(() -> coordinator.loadResult(persisted));
  }

  public Mono<Void> createExecutionOnly(CanonicalExecutionRequest request) {
    return blocking.defer(
        () -> {
          coordinator.createExecutionOnly(request);
          return null;
        });
  }
}
