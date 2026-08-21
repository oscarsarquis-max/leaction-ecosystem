package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.model.IdempotencyRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionRecoveryQueryPort;
import br.com.banco.spider.execution.persistence.port.ExecutionResultStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import br.com.banco.spider.execution.persistence.port.IdempotencyStorePort;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionControlEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionPlanEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionResultEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.ExecutionTransitionEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.entity.IdempotencyRecordEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionControlJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionPlanJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionResultJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.ExecutionTransitionJpaRepository;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.IdempotencyRecordJpaRepository;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import java.time.Instant;
import java.util.EnumSet;
import java.util.List;
import java.util.Optional;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/** Adapters JPA atrás das portas de persistência canônica. */
public final class JpaCanonicalPersistenceAdapters {

  private JpaCanonicalPersistenceAdapters() {}

  @Component
  @ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
  public static class ControlAdapter implements ExecutionControlStorePort {
    private final ExecutionControlJpaRepository repo;

    public ControlAdapter(ExecutionControlJpaRepository repo) {
      this.repo = repo;
    }

    @Override
    public void insert(ExecutionControlRecord record) {
      repo.save(toEntity(record));
    }

    @Override
    public Optional<ExecutionControlRecord> findByExecutionId(String executionId) {
      return repo.findById(executionId).map(ControlAdapter::toModel);
    }

    @Override
    public ExecutionControlRecord updateState(
        String executionId,
        ExecutionState expectedState,
        long expectedVersion,
        ExecutionState newState,
        TechnicalStatus technicalStatus,
        String planId,
        String routeCode,
        String routeVersion,
        String activeWaitType,
        Instant startedAt,
        Instant completedAt,
        Instant lastUpdatedAt) {
      ExecutionControlEntity e =
          repo.findById(executionId)
              .orElseThrow(() -> new IllegalStateException("Execution not found: " + executionId));
      if (e.getState() != expectedState || e.getStateVersion() != expectedVersion) {
        throw new InMemoryExecutionControlStore.OptimisticLockException(
            "State/version mismatch for " + executionId);
      }
      e.setState(newState);
      e.setStateVersion(e.getStateVersion() + 1);
      if (technicalStatus != null) {
        e.setTechnicalStatus(technicalStatus);
      }
      if (planId != null) {
        e.setPlanId(planId);
      }
      if (routeCode != null) {
        e.setRouteCode(routeCode);
      }
      if (routeVersion != null) {
        e.setRouteVersion(routeVersion);
      }
      if (activeWaitType != null) {
        e.setActiveWaitType(activeWaitType);
      }
      if (startedAt != null) {
        e.setStartedAt(startedAt);
      }
      if (completedAt != null) {
        e.setCompletedAt(completedAt);
      }
      e.setLastUpdatedAt(lastUpdatedAt);
      return toModel(repo.save(e));
    }

    @Override
    public List<ExecutionControlRecord> findByStates(List<ExecutionState> states) {
      return repo.findByStateIn(states).stream().map(ControlAdapter::toModel).toList();
    }

    @Override
    public List<ExecutionControlRecord> listRecent(
        int limit, Instant cursorStartedAt, String cursorExecutionId) {
      List<ExecutionControlRecord> all =
          repo.findAll().stream()
              .map(ControlAdapter::toModel)
              .sorted(
                  (a, b) -> {
                    Instant as = a.startedAt() == null ? Instant.EPOCH : a.startedAt();
                    Instant bs = b.startedAt() == null ? Instant.EPOCH : b.startedAt();
                    int c = bs.compareTo(as);
                    if (c != 0) {
                      return c;
                    }
                    return b.executionId().compareTo(a.executionId());
                  })
              .filter(
                  r -> {
                    if (cursorStartedAt == null || cursorExecutionId == null) {
                      return true;
                    }
                    Instant s = r.startedAt() == null ? Instant.EPOCH : r.startedAt();
                    int cmp = s.compareTo(cursorStartedAt);
                    if (cmp < 0) {
                      return true;
                    }
                    if (cmp > 0) {
                      return false;
                    }
                    return r.executionId().compareTo(cursorExecutionId) < 0;
                  })
              .limit(Math.max(1, Math.min(limit, 50)))
              .toList();
      return all;
    }

    static ExecutionControlEntity toEntity(ExecutionControlRecord r) {
      ExecutionControlEntity e = new ExecutionControlEntity();
      e.setExecutionId(r.executionId());
      e.setContextId(r.contextId());
      e.setCorrelationId(r.correlationId());
      e.setPlanId(r.planId());
      e.setRouteCode(r.routeCode());
      e.setRouteVersion(r.routeVersion());
      e.setState(r.state());
      e.setStateVersion(r.stateVersion());
      e.setTechnicalStatus(r.technicalStatus());
      e.setStartedAt(r.startedAt());
      e.setCompletedAt(r.completedAt());
      e.setLastUpdatedAt(r.lastUpdatedAt());
      e.setActiveWaitType(r.activeWaitType());
      e.setRetentionClassRef(r.retentionClassRef());
      e.setOwnerPrincipalRef(r.ownerPrincipalRef());
      return e;
    }

    static ExecutionControlRecord toModel(ExecutionControlEntity e) {
      return new ExecutionControlRecord(
          e.getExecutionId(),
          e.getContextId(),
          e.getCorrelationId(),
          e.getPlanId(),
          e.getRouteCode(),
          e.getRouteVersion(),
          e.getState(),
          e.getStateVersion(),
          e.getTechnicalStatus(),
          e.getStartedAt(),
          e.getCompletedAt(),
          e.getLastUpdatedAt(),
          e.getActiveWaitType(),
          e.getRetentionClassRef(),
          e.getOwnerPrincipalRef());
    }
  }

  @Component
  @ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
  public static class PlanAdapter implements ExecutionPlanStorePort {
    private final ExecutionPlanJpaRepository repo;

    public PlanAdapter(ExecutionPlanJpaRepository repo) {
      this.repo = repo;
    }

    @Override
    public void insert(PersistedExecutionPlan plan) {
      ExecutionPlanEntity e = new ExecutionPlanEntity();
      e.setPlanId(plan.planId());
      e.setExecutionId(plan.executionId());
      e.setRouteCode(plan.routeCode());
      e.setRouteVersion(plan.routeVersion());
      e.setJourneyRef(plan.journeyRef());
      e.setCreatedAt(plan.createdAt());
      e.setIntegrityRef(plan.integrityRef());
      e.setSchemaVersion(plan.schemaVersion());
      e.setCanonicalPlanRepresentation(plan.canonicalPlanRepresentation());
      repo.save(e);
    }

    @Override
    public Optional<PersistedExecutionPlan> findByPlanId(String planId) {
      return repo.findById(planId).map(PlanAdapter::toModel);
    }

    @Override
    public Optional<PersistedExecutionPlan> findByExecutionId(String executionId) {
      return repo.findByExecutionId(executionId).map(PlanAdapter::toModel);
    }

    static PersistedExecutionPlan toModel(ExecutionPlanEntity e) {
      return new PersistedExecutionPlan(
          e.getPlanId(),
          e.getExecutionId(),
          e.getRouteCode(),
          e.getRouteVersion(),
          e.getJourneyRef(),
          e.getCreatedAt(),
          e.getIntegrityRef(),
          e.getSchemaVersion(),
          e.getCanonicalPlanRepresentation());
    }
  }

  @Component
  @ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
  public static class TransitionAdapter implements ExecutionTransitionStorePort {
    private final ExecutionTransitionJpaRepository repo;

    public TransitionAdapter(ExecutionTransitionJpaRepository repo) {
      this.repo = repo;
    }

    @Override
    public void append(ExecutionTransitionRecord transition) {
      ExecutionTransitionEntity e = new ExecutionTransitionEntity();
      e.setTransitionId(transition.transitionId());
      e.setExecutionId(transition.executionId());
      e.setSequenceNo(transition.sequence());
      e.setPreviousState(transition.previousState());
      e.setNewState(transition.newState());
      e.setReasonCode(transition.reasonCode());
      e.setOccurredAt(transition.occurredAt());
      e.setAttemptId(transition.attemptId());
      repo.save(e);
    }

    @Override
    public List<ExecutionTransitionRecord> findByExecutionId(String executionId) {
      return repo.findByExecutionIdOrderBySequenceNoAsc(executionId).stream()
          .map(
              e ->
                  new ExecutionTransitionRecord(
                      e.getTransitionId(),
                      e.getExecutionId(),
                      e.getSequenceNo(),
                      e.getPreviousState(),
                      e.getNewState(),
                      e.getReasonCode(),
                      e.getOccurredAt(),
                      e.getAttemptId()))
          .toList();
    }

    @Override
    public long nextSequence(String executionId) {
      return repo.maxSequence(executionId) + 1;
    }
  }

  @Component
  @ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
  public static class ResultAdapter implements ExecutionResultStorePort {
    private final ExecutionResultJpaRepository repo;

    public ResultAdapter(ExecutionResultJpaRepository repo) {
      this.repo = repo;
    }

    @Override
    public void insert(PersistedExecutionResult result) {
      ExecutionResultEntity e = new ExecutionResultEntity();
      e.setResultRef(result.resultRef());
      e.setExecutionId(result.executionId());
      e.setContractVersion(result.contractVersion());
      e.setState(result.state());
      e.setTechnicalStatus(result.technicalStatus());
      e.setResultRepresentation(result.resultRepresentation());
      e.setContentDigest(result.contentDigest());
      e.setCreatedAt(result.createdAt());
      e.setExpiresAt(result.expiresAt());
      repo.save(e);
    }

    @Override
    public void replaceByExecutionId(PersistedExecutionResult result) {
      repo.findByExecutionId(result.executionId()).ifPresent(repo::delete);
      insert(result);
    }

    @Override
    public Optional<PersistedExecutionResult> findByResultRef(String resultRef) {
      return repo.findById(resultRef).map(ResultAdapter::toModel);
    }

    @Override
    public Optional<PersistedExecutionResult> findByExecutionId(String executionId) {
      return repo.findByExecutionId(executionId).map(ResultAdapter::toModel);
    }

    static PersistedExecutionResult toModel(ExecutionResultEntity e) {
      return new PersistedExecutionResult(
          e.getResultRef(),
          e.getExecutionId(),
          e.getContractVersion(),
          e.getState(),
          e.getTechnicalStatus(),
          e.getResultRepresentation(),
          e.getContentDigest(),
          e.getCreatedAt(),
          e.getExpiresAt());
    }
  }

  @Component
  @ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
  public static class IdempotencyAdapter implements IdempotencyStorePort {
    private final IdempotencyRecordJpaRepository repo;

    public IdempotencyAdapter(IdempotencyRecordJpaRepository repo) {
      this.repo = repo;
    }

    @Override
    public void insert(IdempotencyRecord record) {
      IdempotencyRecordEntity e = new IdempotencyRecordEntity();
      e.setIdempotencyRecordId(record.idempotencyRecordId());
      e.setScopeHash(record.scopeHash());
      e.setIdempotencyKeyHash(record.idempotencyKeyHash());
      e.setRequestFingerprint(record.requestFingerprint());
      e.setFingerprintVersion(record.fingerprintVersion());
      e.setExecutionId(record.executionId());
      e.setState(record.state());
      e.setResultRef(record.resultRef());
      e.setCreatedAt(record.createdAt());
      e.setUpdatedAt(record.updatedAt());
      e.setExpiresAt(record.expiresAt());
      e.setRecordVersion(record.recordVersion());
      repo.save(e);
    }

    @Override
    public Optional<IdempotencyRecord> findByScopeAndKeyHash(
        String scopeHash, String idempotencyKeyHash) {
      return repo.findByScopeHashAndIdempotencyKeyHash(scopeHash, idempotencyKeyHash)
          .map(IdempotencyAdapter::toModel);
    }

    @Override
    public IdempotencyRecord update(
        String idempotencyRecordId,
        long expectedVersion,
        IdempotencyRecordState newState,
        String resultRef,
        Instant updatedAt) {
      IdempotencyRecordEntity e =
          repo.findById(idempotencyRecordId)
              .orElseThrow(() -> new IllegalStateException("Idempotency record not found"));
      if (e.getRecordVersion() != expectedVersion) {
        throw new IllegalStateException("Idempotency version mismatch");
      }
      e.setState(newState);
      if (resultRef != null) {
        e.setResultRef(resultRef);
      }
      e.setUpdatedAt(updatedAt);
      e.setRecordVersion(e.getRecordVersion() + 1);
      return toModel(repo.save(e));
    }

    static IdempotencyRecord toModel(IdempotencyRecordEntity e) {
      return new IdempotencyRecord(
          e.getIdempotencyRecordId(),
          e.getScopeHash(),
          e.getIdempotencyKeyHash(),
          e.getRequestFingerprint(),
          e.getFingerprintVersion(),
          e.getExecutionId(),
          e.getState(),
          e.getResultRef(),
          e.getCreatedAt(),
          e.getUpdatedAt(),
          e.getExpiresAt(),
          e.getRecordVersion());
    }
  }

  @Component
  @ConditionalOnProperty(name = "spider.canonical.persistence.mode", havingValue = "jpa")
  public static class RecoveryAdapter implements ExecutionRecoveryQueryPort {
    private final ExecutionControlStorePort controlStore;
    private final ExecutionPlanStorePort planStore;

    public RecoveryAdapter(ExecutionControlStorePort controlStore, ExecutionPlanStorePort planStore) {
      this.controlStore = controlStore;
      this.planStore = planStore;
    }

    @Override
    public Optional<ExecutionControlRecord> findByExecutionId(String executionId) {
      return controlStore.findByExecutionId(executionId);
    }

    @Override
    public List<ExecutionControlRecord> findRecoverableExecutions() {
      return controlStore.findByStates(
          List.copyOf(
              EnumSet.of(
                  ExecutionState.RECEIVED,
                  ExecutionState.VALIDATED,
                  ExecutionState.RESOLVED,
                  ExecutionState.PLANNED,
                  ExecutionState.RUNNING,
                  ExecutionState.WAITING_EXTERNAL,
                  ExecutionState.COMPENSATING)));
    }

    @Override
    public Optional<PersistedExecutionPlan> findPlanByExecutionId(String executionId) {
      return planStore.findByExecutionId(executionId);
    }
  }
}
