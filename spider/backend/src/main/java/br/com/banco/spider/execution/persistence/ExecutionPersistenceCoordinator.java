package br.com.banco.spider.execution.persistence;

import br.com.banco.spider.canonical.contract.CanonicalExecutionRequest;
import br.com.banco.spider.canonical.contract.CanonicalExecutionResult;
import br.com.banco.spider.execution.callback.CallbackOutboxCreationService;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.fingerprint.CanonicalRequestFingerprintPort;
import br.com.banco.spider.execution.fingerprint.IdempotencyKeyHashPort;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyRecordState;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyReservationResult;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyReservationStatus;
import br.com.banco.spider.execution.persistence.idempotency.IdempotencyScope;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.model.IdempotencyRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionResult;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionResultStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import br.com.banco.spider.execution.persistence.port.IdempotencyStorePort;
import br.com.banco.spider.execution.plan.ExecutionPlan;
import br.com.banco.spider.execution.plan.ExecutionPlanNode;
import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryIdempotencyStore;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Coordenação bloqueante das operações atômicas de controle.
 * Deve ser invocada apenas via {@link ReactiveExecutionPersistenceGateway}.
 */
@Service
public class ExecutionPersistenceCoordinator {

  private static final Logger log = LoggerFactory.getLogger(ExecutionPersistenceCoordinator.class);

  private final ExecutionControlStorePort controlStore;
  private final ExecutionPlanStorePort planStore;
  private final ExecutionTransitionStorePort transitionStore;
  private final ExecutionResultStorePort resultStore;
  private final IdempotencyStorePort idempotencyStore;
  private final ExecutionStepStorePort stepStore;
  private final CanonicalRequestFingerprintPort fingerprintPort;
  private final IdempotencyKeyHashPort keyHashPort;
  private final CanonicalExecutionResultSerializer resultSerializer;
  private final IdentifierGenerator ids;
  private final SpiderClock clock;
  private final Duration idempotencyTtl;
  private final Duration resultTtl;
  private final CallbackOutboxCreationService outboxCreation;

  @org.springframework.beans.factory.annotation.Autowired
  public ExecutionPersistenceCoordinator(
      ExecutionControlStorePort controlStore,
      ExecutionPlanStorePort planStore,
      ExecutionTransitionStorePort transitionStore,
      ExecutionResultStorePort resultStore,
      IdempotencyStorePort idempotencyStore,
      ExecutionStepStorePort stepStore,
      CanonicalRequestFingerprintPort fingerprintPort,
      IdempotencyKeyHashPort keyHashPort,
      CanonicalExecutionResultSerializer resultSerializer,
      IdentifierGenerator ids,
      SpiderClock clock,
      @Value("${spider.canonical.persistence.idempotency.ttl:PT24H}") Duration idempotencyTtl,
      @Value("${spider.canonical.persistence.result.ttl:PT24H}") Duration resultTtl,
      @org.springframework.beans.factory.annotation.Autowired(required = false)
          CallbackOutboxCreationService outboxCreation) {
    this.controlStore = controlStore;
    this.planStore = planStore;
    this.transitionStore = transitionStore;
    this.resultStore = resultStore;
    this.idempotencyStore = idempotencyStore;
    this.stepStore = stepStore;
    this.fingerprintPort = fingerprintPort;
    this.keyHashPort = keyHashPort;
    this.resultSerializer = resultSerializer;
    this.ids = ids;
    this.clock = clock;
    this.idempotencyTtl = idempotencyTtl;
    this.resultTtl = resultTtl;
    this.outboxCreation = outboxCreation;
  }

  /** Compatível com montagem de testes sem callback. */
  public ExecutionPersistenceCoordinator(
      ExecutionControlStorePort controlStore,
      ExecutionPlanStorePort planStore,
      ExecutionTransitionStorePort transitionStore,
      ExecutionResultStorePort resultStore,
      IdempotencyStorePort idempotencyStore,
      ExecutionStepStorePort stepStore,
      CanonicalRequestFingerprintPort fingerprintPort,
      IdempotencyKeyHashPort keyHashPort,
      CanonicalExecutionResultSerializer resultSerializer,
      IdentifierGenerator ids,
      SpiderClock clock,
      Duration idempotencyTtl,
      Duration resultTtl) {
    this(
        controlStore,
        planStore,
        transitionStore,
        resultStore,
        idempotencyStore,
        stepStore,
        fingerprintPort,
        keyHashPort,
        resultSerializer,
        ids,
        clock,
        idempotencyTtl,
        resultTtl,
        null);
  }

  @Transactional
  public IdempotencyReservationResult reserveOrCreate(
      CanonicalExecutionRequest request,
      IdempotencyScope scope,
      String rawKey,
      boolean createWithoutKey) {
    return reserveOrCreate(request, scope, rawKey, createWithoutKey, null);
  }

  public IdempotencyReservationResult reserveOrCreate(
      CanonicalExecutionRequest request,
      IdempotencyScope scope,
      String rawKey,
      boolean createWithoutKey,
      String ownerPrincipalRef) {

    Instant now = clock.now();

    if (rawKey == null || rawKey.isBlank()) {
      if (!createWithoutKey) {
        return IdempotencyReservationResult.notApplicable();
      }
      createExecutionOnly(request, ownerPrincipalRef);
      log.info("event=idempotency_skipped executionId={}", request.execution().executionId());
      return IdempotencyReservationResult.notApplicable();
    }

    String scopeHash = scope.scopeHash();
    String keyHash = keyHashPort.hash(rawKey);
    var fp = fingerprintPort.fingerprint(request);

    Optional<IdempotencyRecord> existing = idempotencyStore.findByScopeAndKeyHash(scopeHash, keyHash);
    if (existing.isPresent()) {
      return mapExisting(existing.get(), fp.digest(), now);
    }

    try {
      String executionId = request.execution().executionId();
      IdempotencyRecord record =
          new IdempotencyRecord(
              ids.nextId("idem"),
              scopeHash,
              keyHash,
              fp.digest(),
              fp.version(),
              executionId,
              IdempotencyRecordState.RESERVED,
              null,
              now,
              now,
              now.plus(idempotencyTtl),
              0L);
      idempotencyStore.insert(record);
      createExecutionOnly(request, ownerPrincipalRef);
      log.info("event=idempotency_reserved executionId={} reasonCode=IDEMPOTENCY_RESERVED", executionId);
      return IdempotencyReservationResult.reservedNew(executionId);
    } catch (InMemoryIdempotencyStore.DuplicateIdempotencyException
        | org.springframework.dao.DataIntegrityViolationException ex) {
      IdempotencyRecord raced =
          idempotencyStore
              .findByScopeAndKeyHash(scopeHash, keyHash)
              .orElseThrow(() -> new IllegalStateException("Idempotency race without record", ex));
      return mapExisting(raced, fp.digest(), now);
    }
  }

  private IdempotencyReservationResult mapExisting(
      IdempotencyRecord record, String fingerprint, Instant now) {
    if (record.expiresAt().isBefore(now)
        && record.state() != IdempotencyRecordState.IN_PROGRESS
        && record.state() != IdempotencyRecordState.RESERVED) {
      return new IdempotencyReservationResult(
          IdempotencyReservationStatus.EXPIRED_REUSABLE_KEY,
          record.executionId(),
          null,
          record.resultRef(),
          "IDEMPOTENCY_EXPIRED");
    }
    if (!record.requestFingerprint().equals(fingerprint)) {
      log.info(
          "event=idempotency_conflict executionId={} reasonCode=IDEMPOTENCY_CONFLICT",
          record.executionId());
      return new IdempotencyReservationResult(
          IdempotencyReservationStatus.CONFLICTING_REQUEST,
          record.executionId(),
          null,
          null,
          "IDEMPOTENCY_CONFLICT");
    }

    Optional<ExecutionControlRecord> control =
        controlStore.findByExecutionId(record.executionId());
    ExecutionState state = control.map(ExecutionControlRecord::state).orElse(null);

    return switch (record.state()) {
      case RESERVED, IN_PROGRESS -> {
        log.info(
            "event=idempotency_in_progress_reused executionId={} reasonCode=IN_PROGRESS_SAME_REQUEST",
            record.executionId());
        yield new IdempotencyReservationResult(
            IdempotencyReservationStatus.IN_PROGRESS_SAME_REQUEST,
            record.executionId(),
            state,
            record.resultRef(),
            "IN_PROGRESS_SAME_REQUEST");
      }
      case COMPLETED -> {
        log.info(
            "event=idempotency_result_reused executionId={} reasonCode=COMPLETED_SAME_REQUEST",
            record.executionId());
        yield new IdempotencyReservationResult(
            IdempotencyReservationStatus.COMPLETED_SAME_REQUEST,
            record.executionId(),
            state != null ? state : ExecutionState.SUCCEEDED,
            record.resultRef(),
            "COMPLETED_SAME_REQUEST");
      }
      case FAILED_REUSABLE -> new IdempotencyReservationResult(
          IdempotencyReservationStatus.FAILED_SAME_REQUEST,
          record.executionId(),
          state,
          record.resultRef(),
          "FAILED_SAME_REQUEST");
      case UNKNOWN -> new IdempotencyReservationResult(
          IdempotencyReservationStatus.UNKNOWN_SAME_REQUEST,
          record.executionId(),
          state != null ? state : ExecutionState.WAITING_EXTERNAL,
          record.resultRef(),
          "UNKNOWN_SAME_REQUEST");
      case CONFLICT, EXPIRED -> new IdempotencyReservationResult(
          IdempotencyReservationStatus.CONFLICTING_REQUEST,
          record.executionId(),
          state,
          null,
          "IDEMPOTENCY_CONFLICT");
    };
  }

  @Transactional
  public void createExecutionOnly(CanonicalExecutionRequest request) {
    Instant now = clock.now();
    ExecutionControlRecord control =
        new ExecutionControlRecord(
            request.execution().executionId(),
            request.contextRef().contextId(),
            request.trace().correlationId(),
            null,
            null,
            null,
            ExecutionState.RECEIVED,
            0L,
            null,
            null,
            null,
            now,
            null,
            "retention:technical-default@1",
            null);
    controlStore.insert(control);
    appendTransition(request.execution().executionId(), null, ExecutionState.RECEIVED, "REQUEST_RECEIVED", now);
    log.info("event=execution_persisted executionId={} state=RECEIVED", request.execution().executionId());
  }

  @Transactional
  public void createExecutionOnly(CanonicalExecutionRequest request, String ownerPrincipalRef) {
    Instant now = clock.now();
    ExecutionControlRecord control =
        new ExecutionControlRecord(
            request.execution().executionId(),
            request.contextRef().contextId(),
            request.trace().correlationId(),
            null,
            null,
            null,
            ExecutionState.RECEIVED,
            0L,
            null,
            null,
            null,
            now,
            null,
            "retention:technical-default@1",
            ownerPrincipalRef);
    controlStore.insert(control);
    appendTransition(request.execution().executionId(), null, ExecutionState.RECEIVED, "REQUEST_RECEIVED", now);
    log.info("event=execution_persisted executionId={} state=RECEIVED", request.execution().executionId());
  }

  @Transactional
  public ExecutionControlRecord transition(
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
    Instant now = clock.now();
    Instant startedAt = newState == ExecutionState.RUNNING ? now : null;
    Instant completedAt =
        newState.isTerminal() || newState == ExecutionState.WAITING_EXTERNAL ? now : null;
    ExecutionControlRecord updated =
        controlStore.updateState(
            executionId,
            expectedState,
            expectedVersion,
            newState,
            technicalStatus,
            planId,
            routeCode,
            routeVersion,
            activeWaitType,
            startedAt,
            completedAt,
            now);
    appendTransition(executionId, expectedState, newState, reasonCode, now);
    log.info(
        "event=transition_persisted executionId={} from={} to={} reasonCode={}",
        executionId,
        expectedState,
        newState,
        reasonCode);
    return updated;
  }

  @Transactional
  public ExecutionControlRecord persistPlan(ExecutionPlan plan, long expectedVersion) {
    Instant now = clock.now();
    PersistedExecutionPlan persisted =
        new PersistedExecutionPlan(
            plan.planId(),
            plan.executionId(),
            plan.routeRef().routeCode(),
            plan.routeRef().routeVersion(),
            plan.journeyRef(),
            plan.createdAt(),
            plan.integrityRef(),
            "1.0",
            plan.canonicalRepresentation());
    planStore.insert(persisted);

    List<ExecutionStepRecord> steps = new ArrayList<>();
    for (ExecutionPlanNode node : plan.orderedNodes()) {
      StepState initial = node.orderedPosition() == 0 ? StepState.READY : StepState.PENDING;
      steps.add(
          new ExecutionStepRecord(
              plan.executionId(),
              node.stepId(),
              node.orderedPosition(),
              initial,
              0L,
              null,
              null,
              null,
              null,
              null,
              now));
    }
    stepStore.insertAll(steps);
    log.info(
        "event=steps_persisted executionId={} count={} firstReady={}",
        plan.executionId(),
        steps.size(),
        steps.isEmpty() ? null : steps.getFirst().stepId());

    return transition(
        plan.executionId(),
        ExecutionState.RESOLVED,
        expectedVersion,
        ExecutionState.PLANNED,
        "PLAN_MATERIALIZED",
        null,
        plan.planId(),
        plan.routeRef().routeCode(),
        plan.routeRef().routeVersion(),
        null);
  }

  @Transactional
  public PersistedExecutionResult persistTerminalResult(
      CanonicalExecutionResult result,
      IdempotencyRecordState idempotencyState,
      String scopeHash,
      String keyHash) {
    Instant now = clock.now();
    var serialized = resultSerializer.serialize(result);
    String resultRef = ids.nextId("res");
    PersistedExecutionResult persisted =
        new PersistedExecutionResult(
            resultRef,
            result.execution().executionId(),
            result.contract().contractVersion(),
            result.state(),
            result.outcome().technicalStatus(),
            serialized.representation(),
            serialized.contentDigest(),
            now,
            now.plus(resultTtl));
    if (resultStore.findByExecutionId(result.execution().executionId()).isPresent()) {
      resultStore.replaceByExecutionId(persisted);
    } else {
      resultStore.insert(persisted);
    }

    if (scopeHash != null && keyHash != null) {
      idempotencyStore
          .findByScopeAndKeyHash(scopeHash, keyHash)
          .ifPresent(
              rec ->
                  idempotencyStore.update(
                      rec.idempotencyRecordId(),
                      rec.recordVersion(),
                      idempotencyState,
                      resultRef,
                      now));
    }
    log.info(
        "event=result_persisted executionId={} state={} reasonCode=RESULT_STORED",
        result.execution().executionId(),
        result.state());
    if (outboxCreation != null) {
      outboxCreation.createIfRequired(result, persisted);
    }
    return persisted;
  }

  @Transactional
  public void markIdempotencyInProgress(String scopeHash, String keyHash) {
    if (scopeHash == null || keyHash == null) {
      return;
    }
    idempotencyStore
        .findByScopeAndKeyHash(scopeHash, keyHash)
        .ifPresent(
            rec -> {
              if (rec.state() == IdempotencyRecordState.RESERVED) {
                idempotencyStore.update(
                    rec.idempotencyRecordId(),
                    rec.recordVersion(),
                    IdempotencyRecordState.IN_PROGRESS,
                    null,
                    clock.now());
              }
            });
  }

  public Optional<PersistedExecutionResult> findResult(String resultRef) {
    return resultStore.findByResultRef(resultRef);
  }

  public Optional<PersistedExecutionResult> findResultByExecutionId(String executionId) {
    return resultStore.findByExecutionId(executionId);
  }

  public Optional<ExecutionControlRecord> findControl(String executionId) {
    return controlStore.findByExecutionId(executionId);
  }

  public Optional<PersistedExecutionPlan> findPlan(String executionId) {
    return planStore.findByExecutionId(executionId);
  }

  public CanonicalExecutionResult loadResult(PersistedExecutionResult persisted) {
    return resultSerializer.deserialize(persisted.resultRepresentation(), persisted.contentDigest());
  }

  private void appendTransition(
      String executionId,
      ExecutionState previous,
      ExecutionState next,
      String reasonCode,
      Instant at) {
    long seq = transitionStore.nextSequence(executionId);
    transitionStore.append(
        new ExecutionTransitionRecord(
            ids.nextId("tr"), executionId, seq, previous, next, reasonCode, at, null));
  }
}
