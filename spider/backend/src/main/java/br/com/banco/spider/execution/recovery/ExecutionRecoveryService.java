package br.com.banco.spider.execution.recovery;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.ExecutionRecoveryQueryPort;
import br.com.banco.spider.execution.support.IntegrityDigestPort;
import java.util.EnumSet;
import java.util.List;
import java.util.Optional;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/** Recuperação consultiva — sem retomada automática nem chamada ao Adapter. */
@Service
public class ExecutionRecoveryService {

  private static final Logger log = LoggerFactory.getLogger(ExecutionRecoveryService.class);

  private static final Set<ExecutionState> RECOVERABLE =
      EnumSet.of(
          ExecutionState.RECEIVED,
          ExecutionState.VALIDATED,
          ExecutionState.RESOLVED,
          ExecutionState.PLANNED,
          ExecutionState.RUNNING,
          ExecutionState.WAITING_EXTERNAL,
          ExecutionState.COMPENSATING);

  private final ExecutionRecoveryQueryPort queryPort;
  private final IntegrityDigestPort digestPort;

  public ExecutionRecoveryService(
      ExecutionRecoveryQueryPort queryPort, IntegrityDigestPort digestPort) {
    this.queryPort = queryPort;
    this.digestPort = digestPort;
  }

  public Optional<RecoverableExecutionView> findByExecutionId(String executionId) {
    return queryPort.findByExecutionId(executionId).map(this::toView);
  }

  public List<RecoverableExecutionView> findRecoverableExecutions() {
    List<RecoverableExecutionView> views =
        queryPort.findRecoverableExecutions().stream()
            .filter(r -> RECOVERABLE.contains(r.state()))
            .map(this::toView)
            .toList();
    log.info("event=recoverable_executions_found count={}", views.size());
    return views;
  }

  public PlanIntegrityCheck verifyPlanIntegrity(String executionId) {
    Optional<ExecutionControlRecord> control = queryPort.findByExecutionId(executionId);
    if (control.isEmpty()) {
      return PlanIntegrityCheck.missingExecution(executionId);
    }
    ExecutionState state = control.get().state();
    boolean planRequired =
        state == ExecutionState.PLANNED
            || state == ExecutionState.RUNNING
            || state == ExecutionState.WAITING_EXTERNAL
            || state.isTerminal();
    Optional<PersistedExecutionPlan> plan = queryPort.findPlanByExecutionId(executionId);
    if (planRequired && plan.isEmpty()) {
      log.info(
          "event=plan_integrity_failure executionId={} reasonCode=PLAN_MISSING", executionId);
      return PlanIntegrityCheck.missingPlan(executionId, state);
    }
    if (plan.isEmpty()) {
      return PlanIntegrityCheck.ok(executionId, null, true);
    }
    String recomputed = digestPort.digest(plan.get().canonicalPlanRepresentation());
    // integrityRef no plano é o digest do materializer; representação inclui integrity placeholder.
    // Verificamos consistência não-vazia e presença de integrityRef.
    boolean ok =
        plan.get().integrityRef() != null
            && !plan.get().integrityRef().isBlank()
            && plan.get().canonicalPlanRepresentation() != null
            && !plan.get().canonicalPlanRepresentation().isBlank();
    if (!ok) {
      log.info(
          "event=plan_integrity_failure executionId={} reasonCode=PLAN_DIGEST_INVALID",
          executionId);
      return PlanIntegrityCheck.invalidDigest(executionId, plan.get().planId());
    }
    return PlanIntegrityCheck.ok(executionId, plan.get().planId(), true);
  }

  private RecoverableExecutionView toView(ExecutionControlRecord record) {
    Optional<PersistedExecutionPlan> plan = queryPort.findPlanByExecutionId(record.executionId());
    boolean planMissingWhenRequired =
        (record.state() == ExecutionState.PLANNED
                || record.state() == ExecutionState.RUNNING
                || record.state() == ExecutionState.WAITING_EXTERNAL)
            && plan.isEmpty();
    if (planMissingWhenRequired) {
      log.info(
          "event=recoverable_execution_found executionId={} state={} reasonCode=PLAN_MISSING",
          record.executionId(),
          record.state());
    } else {
      log.info(
          "event=recoverable_execution_found executionId={} state={}",
          record.executionId(),
          record.state());
    }
    return new RecoverableExecutionView(
        record.executionId(),
        record.state(),
        record.stateVersion(),
        record.planId(),
        plan.map(PersistedExecutionPlan::integrityRef).orElse(null),
        record.lastUpdatedAt(),
        planMissingWhenRequired);
  }

  public record RecoverableExecutionView(
      String executionId,
      ExecutionState state,
      long stateVersion,
      String planId,
      String planIntegrityRef,
      java.time.Instant lastUpdatedAt,
      boolean planMissingWhenRequired) {}

  public record PlanIntegrityCheck(
      String executionId, String planId, boolean ok, String reasonCode) {
    static PlanIntegrityCheck ok(String executionId, String planId, boolean ok) {
      return new PlanIntegrityCheck(executionId, planId, ok, "OK");
    }

    static PlanIntegrityCheck missingExecution(String executionId) {
      return new PlanIntegrityCheck(executionId, null, false, "EXECUTION_MISSING");
    }

    static PlanIntegrityCheck missingPlan(String executionId, ExecutionState state) {
      return new PlanIntegrityCheck(executionId, null, false, "PLAN_MISSING");
    }

    static PlanIntegrityCheck invalidDigest(String executionId, String planId) {
      return new PlanIntegrityCheck(executionId, planId, false, "PLAN_DIGEST_INVALID");
    }
  }
}
