package br.com.banco.spider.application.console;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionTransitionRecord;
import br.com.banco.spider.execution.persistence.model.PersistedExecutionPlan;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.CallbackReconciliationStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionPlanStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionStepStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionTransitionStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.step.ExecutionStepRecord;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.step.StepState;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.governance.port.ExecutionGovernanceFixationStorePort;
import br.com.banco.spider.operational.readmodel.ListOperationalExecutionsQuery;
import br.com.banco.spider.operational.readmodel.OperationalExecutionDetail;
import br.com.banco.spider.operational.readmodel.OperationalExecutionListItem;
import br.com.banco.spider.operational.readmodel.OperationalRedactionService;
import br.com.banco.spider.operational.readmodel.OperationalSection;
import br.com.banco.spider.operational.readmodel.OperationalTimelineEvent;
import br.com.banco.spider.operational.readmodel.OperationalTimelinePhase;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

@Service
public class OperationalConsoleQueryService {

  private final ExecutionControlStorePort controlStore;
  private final ExecutionPlanStorePort planStore;
  private final ExecutionStepStorePort stepStore;
  private final StepAttemptStorePort attemptStore;
  private final ExecutionTransitionStorePort transitionStore;
  private final ExecutionWaitStorePort waitStore;
  private final ObjectProvider<CallbackOutboxStorePort> outboxStore;
  private final ObjectProvider<CallbackReconciliationStorePort> reconciliationStore;
  private final ObjectProvider<ExecutionGovernanceFixationStorePort> fixationStore;
  private final OperationalRedactionService redaction;
  private final int maxPageSize;
  private final int defaultPageSize;
  private final boolean safeProjectionsEnabled;

  public OperationalConsoleQueryService(
      ExecutionControlStorePort controlStore,
      ExecutionPlanStorePort planStore,
      ExecutionStepStorePort stepStore,
      StepAttemptStorePort attemptStore,
      ExecutionTransitionStorePort transitionStore,
      ExecutionWaitStorePort waitStore,
      ObjectProvider<CallbackOutboxStorePort> outboxStore,
      ObjectProvider<CallbackReconciliationStorePort> reconciliationStore,
      ObjectProvider<ExecutionGovernanceFixationStorePort> fixationStore,
      OperationalRedactionService redaction,
      @Value("${spider.console.max-page-size:50}") int maxPageSize,
      @Value("${spider.console.default-page-size:20}") int defaultPageSize,
      @Value("${spider.console.safe-projections.enabled:false}") boolean safeProjectionsEnabled) {
    this.controlStore = controlStore;
    this.planStore = planStore;
    this.stepStore = stepStore;
    this.attemptStore = attemptStore;
    this.transitionStore = transitionStore;
    this.waitStore = waitStore;
    this.outboxStore = outboxStore;
    this.reconciliationStore = reconciliationStore;
    this.fixationStore = fixationStore;
    this.redaction = redaction;
    this.maxPageSize = Math.max(1, Math.min(maxPageSize, 100));
    this.defaultPageSize = Math.max(1, Math.min(defaultPageSize, this.maxPageSize));
    this.safeProjectionsEnabled = safeProjectionsEnabled;
  }

  public Mono<ListPage> list(ListOperationalExecutionsQuery query) {
    return Mono.fromCallable(() -> listBlocking(query)).subscribeOn(Schedulers.boundedElastic());
  }

  public Mono<Optional<OperationalExecutionDetail>> getDetail(String executionId) {
    return Mono.fromCallable(() -> Optional.ofNullable(detailBlocking(executionId)))
        .subscribeOn(Schedulers.boundedElastic());
  }

  public record ListPage(
      List<OperationalExecutionListItem> items, String nextCursorStartedAt, String nextCursorExecutionId) {}

  private ListPage listBlocking(ListOperationalExecutionsQuery query) {
    int limit = query.limit() <= 0 ? defaultPageSize : Math.min(query.limit(), maxPageSize);
    List<ExecutionControlRecord> raw =
        controlStore.listRecent(limit + 5, query.cursorStartedAt(), query.cursorExecutionId());
    List<OperationalExecutionListItem> items = new ArrayList<>();
    for (ExecutionControlRecord r : raw) {
      if (query.states() != null && !query.states().isEmpty() && !query.states().contains(r.state())) {
        continue;
      }
      if (query.routeCode() != null
          && !query.routeCode().isBlank()
          && !query.routeCode().equals(r.routeCode())) {
        continue;
      }
      if (query.startedFrom() != null
          && r.startedAt() != null
          && r.startedAt().isBefore(query.startedFrom())) {
        continue;
      }
      if (query.startedTo() != null
          && r.startedAt() != null
          && r.startedAt().isAfter(query.startedTo())) {
        continue;
      }
      if (query.onlyWaiting() && r.state() != ExecutionState.WAITING_EXTERNAL) {
        continue;
      }
      items.add(toListItemLite(r));
      if (items.size() >= limit) {
        break;
      }
    }
    String nextStarted = null;
    String nextId = null;
    if (!items.isEmpty()) {
      OperationalExecutionListItem last = items.get(items.size() - 1);
      nextStarted = last.startedAt() == null ? null : last.startedAt().toString();
      nextId = last.executionId();
    }
    return new ListPage(items, nextStarted, nextId);
  }

  private OperationalExecutionDetail detailBlocking(String executionId) {
    ExecutionControlRecord control = controlStore.findByExecutionId(executionId).orElse(null);
    if (control == null) {
      return null;
    }
    OperationalExecutionListItem summary = toListItem(control);
    Optional<PersistedExecutionPlan> planOpt = planStore.findByExecutionId(executionId);
    List<ExecutionStepRecord> steps =
        stepStore.findByExecutionIdOrdered(executionId);
    List<OperationalExecutionDetail.StepView> stepViews = new ArrayList<>();
    for (ExecutionStepRecord s : steps) {
      List<StepAttemptRecord> attempts =
          attemptStore.findByExecutionAndStep(executionId, s.stepId());
      List<OperationalExecutionDetail.AttemptView> attemptViews =
          attempts.stream()
              .sorted(Comparator.comparingInt(StepAttemptRecord::attemptNumber))
              .map(
                  a ->
                      new OperationalExecutionDetail.AttemptView(
                          a.attemptNumber(),
                          a.state() == null ? null : a.state().name(),
                          a.certainty(),
                          a.errorCode(),
                          a.startedAt(),
                          a.completedAt()))
              .toList();
      Long dur =
          durationMs(s.startedAt(), s.completedAt());
      stepViews.add(
          new OperationalExecutionDetail.StepView(
              s.stepId(),
              s.orderedPosition(),
              s.state() == null ? null : s.state().name(),
              s.startedAt(),
              s.completedAt(),
              dur,
              attemptViews.size(),
              attemptViews,
              null,
              s.terminalErrorCode()));
    }

    OperationalSection<OperationalExecutionDetail.PlanView> planSection =
        planOpt
            .map(
                p ->
                    OperationalSection.of(
                        new OperationalExecutionDetail.PlanView(
                            p.planId(),
                            p.routeCode() + "@" + p.routeVersion(),
                            steps.stream().map(ExecutionStepRecord::stepId).toList(),
                            "PLAN_V1",
                            null,
                            null,
                            "binding:redacted")))
            .orElse(OperationalSection.unavailable("PLAN_NOT_FOUND"));

    List<ExecutionWaitRecord> waits = waitStore.findByExecutionId(executionId);
    OperationalSection<OperationalExecutionDetail.WaitView> waitSection =
        waits.isEmpty()
            ? OperationalSection.unavailable("WAIT_NOT_PRESENT")
            : OperationalSection.of(
                new OperationalExecutionDetail.WaitView(
                    waits.getFirst().state().name(),
                    waits.getFirst().expiresAt(),
                    waits.getFirst().signalDefinitionRef(),
                    waits.getFirst().waitType() == null
                        ? null
                        : waits.getFirst().waitType().name()));

    OperationalSection<OperationalExecutionDetail.SignalView> signalSection =
        OperationalSection.unavailable("SIGNAL_SUMMARY_NOT_INDEXED");

    CallbackOutboxStorePort outbox = outboxStore.getIfAvailable();
    OperationalSection<OperationalExecutionDetail.CallbackView> callbackSection =
        OperationalSection.unavailable("CALLBACK_NOT_PRESENT");
    if (outbox != null) {
      Optional<CallbackOutboxRecord> ob = outbox.findByExecutionId(executionId);
      if (ob.isPresent()) {
        CallbackOutboxRecord r = ob.get();
        callbackSection =
            OperationalSection.of(
                new OperationalExecutionDetail.CallbackView(
                    r.state() == null ? null : r.state().name(),
                    r.attemptCount(),
                    r.state() == null ? null : r.state().name(),
                    r.nextAttemptAt() == null ? null : "RETRY_SCHEDULED"));
      }
    }

    CallbackReconciliationStorePort recon = reconciliationStore.getIfAvailable();
    OperationalSection<OperationalExecutionDetail.ReconciliationView> reconSection =
        OperationalSection.unavailable("RECONCILIATION_NOT_PRESENT");
    if (recon != null) {
      var rr = recon.findByExecutionId(executionId);
      if (rr.isPresent()) {
        var r = rr.get();
        reconSection =
            OperationalSection.of(
                new OperationalExecutionDetail.ReconciliationView(
                    r.state() == null ? null : r.state().name(),
                    r.queryCount(),
                    r.nextQueryAt() == null ? null : "QUERY_SCHEDULED"));
      }
    }

    OperationalSection<OperationalExecutionDetail.GovernanceView> govSection =
        OperationalSection.unavailable("GOVERNANCE_FIXATION_ABSENT");
    ExecutionGovernanceFixationStorePort fix = fixationStore.getIfAvailable();
    if (fix != null) {
      var f = fix.findByExecutionId(executionId);
      if (f.isPresent()) {
        var fixation = f.get();
        govSection =
            OperationalSection.of(
                new OperationalExecutionDetail.GovernanceView(
                    fixation.governanceMode() == null
                        ? "CONTROL_PLANE"
                        : fixation.governanceMode().name(),
                    fixation.governanceBundleRef(),
                    "HISTORICAL",
                    fixation.activationSequence(),
                    fixation.fixedAt(),
                    true));
      }
    }

    OperationalSection<OperationalExecutionDetail.SecurityPostureView> security =
        OperationalSection.of(
            new OperationalExecutionDetail.SecurityPostureView(
                "ENFORCED",
                "ENFORCED",
                "UNKNOWN",
                "ACTIVE",
                "NOT_PRESENT",
                "REDACTED"));

    List<OperationalTimelineEvent> timeline = buildTimeline(control, steps, waits, outbox);

    OperationalSection<Map<String, Object>> reqProj =
        safeProjectionsEnabled
            ? OperationalSection.of(
                redaction
                    .redact(
                        Map.of(
                            "routeRef",
                            summary.routeRef() == null ? "" : summary.routeRef(),
                            "correlationRef",
                            summary.correlationRef()),
                        4,
                        256)
                    .projection())
            : OperationalSection.redacted("SAFE_PROJECTIONS_DISABLED");

    return new OperationalExecutionDetail(
        summary,
        planSection,
        OperationalSection.of(stepViews),
        OperationalSection.of(timeline),
        waitSection,
        signalSection,
        callbackSection,
        reconSection,
        govSection,
        security,
        reqProj,
        OperationalSection.redacted("RESULT_PROJECTION_DEFAULT_OFF"));
  }

  private List<OperationalTimelineEvent> buildTimeline(
      ExecutionControlRecord control,
      List<ExecutionStepRecord> steps,
      List<ExecutionWaitRecord> waits,
      CallbackOutboxStorePort outbox) {
    List<OperationalTimelineEvent> events = new ArrayList<>();
    long seq = 0;
    List<ExecutionTransitionRecord> transitions =
        transitionStore.findByExecutionId(control.executionId());
    for (ExecutionTransitionRecord t : transitions) {
      events.add(
          new OperationalTimelineEvent(
              "tr-" + t.sequence(),
              t.occurredAt(),
              t.sequence(),
              OperationalTimelinePhase.PLANNING,
              "STATE_TRANSITION",
              t.newState() == null ? null : t.newState().name(),
              "INFO",
              "Transição " + t.previousState() + " → " + t.newState(),
              t.reasonCode(),
              null,
              null,
              null,
              redactId(control.correlationId()),
              List.of(),
              "PERSISTED"));
      seq = Math.max(seq, t.sequence());
    }
    for (ExecutionStepRecord s : steps) {
      events.add(
          new OperationalTimelineEvent(
              "step-" + s.stepId(),
              s.startedAt() == null ? control.lastUpdatedAt() : s.startedAt(),
              ++seq,
              OperationalTimelinePhase.STEP_EXECUTION,
              "STEP_" + (s.state() == null ? "UNKNOWN" : s.state().name()),
              s.state() == null ? null : s.state().name(),
              s.state() == StepState.FAILED ? "ERROR" : "INFO",
              "Step " + s.stepId(),
              s.terminalErrorCode(),
              s.stepId(),
              null,
              durationMs(s.startedAt(), s.completedAt()),
              null,
              List.of(),
              "PERSISTED"));
      for (StepAttemptRecord a :
          attemptStore.findByExecutionAndStep(control.executionId(), s.stepId())) {
        events.add(
            new OperationalTimelineEvent(
                "att-" + a.attemptId(),
                a.startedAt(),
                ++seq,
                OperationalTimelinePhase.STEP_EXECUTION,
                "ATTEMPT",
                a.state() == null ? null : a.state().name(),
                a.errorCode() == null ? "INFO" : "WARN",
                "Attempt #" + a.attemptNumber(),
                a.errorCode(),
                s.stepId(),
                a.attemptNumber(),
                durationMs(a.startedAt(), a.completedAt()),
                null,
                a.evidenceRefs(),
                "PERSISTED"));
      }
    }
    for (ExecutionWaitRecord w : waits) {
      events.add(
          new OperationalTimelineEvent(
              "wait-" + w.waitId(),
              w.createdAt(),
              ++seq,
              OperationalTimelinePhase.WAITING_EXTERNAL,
              "WAIT_" + w.state().name(),
              w.state().name(),
              "INFO",
              "Wait externo",
              w.resolutionReasonCode(),
              w.stepId(),
              null,
              null,
              null,
              List.of(),
              "PERSISTED"));
    }
    if (outbox != null) {
      var outboxOpt = outbox.findByExecutionId(control.executionId());
      if (outboxOpt.isPresent()) {
        var o = outboxOpt.get();
        long callbackSeq = ++seq;
        events.add(
            new OperationalTimelineEvent(
                "cb-" + o.outboxId(),
                o.createdAt(),
                callbackSeq,
                OperationalTimelinePhase.CALLBACK,
                "CALLBACK_" + (o.state() == null ? "?" : o.state().name()),
                o.state() == null ? null : o.state().name(),
                "INFO",
                "Callback outbox",
                o.lastErrorCode(),
                null,
                o.attemptCount(),
                null,
                null,
                List.of(),
                "PERSISTED"));
      }
    }
    events.sort(
        Comparator.comparing(OperationalTimelineEvent::occurredAt, Comparator.nullsLast(Comparator.naturalOrder()))
            .thenComparingLong(OperationalTimelineEvent::sequence));
    return events;
  }

  private OperationalExecutionListItem toListItemLite(ExecutionControlRecord r) {
    String waitState =
        r.state() == ExecutionState.WAITING_EXTERNAL
            ? (r.activeWaitType() == null ? "WAITING" : r.activeWaitType())
            : null;
    return new OperationalExecutionListItem(
        r.executionId(),
        redactId(r.correlationId()),
        r.routeCode() == null
            ? null
            : r.routeCode() + (r.routeVersion() == null ? "" : "@" + r.routeVersion()),
        r.routeCode(),
        r.state(),
        r.technicalStatus() == null ? TechnicalStatus.PENDING : r.technicalStatus(),
        null,
        0,
        0,
        waitState,
        null,
        null,
        r.startedAt(),
        r.lastUpdatedAt(),
        r.completedAt(),
        durationMs(r.startedAt(), r.completedAt() != null ? r.completedAt() : r.lastUpdatedAt()),
        null);
  }

  private OperationalExecutionListItem toListItem(ExecutionControlRecord r) {
    List<ExecutionStepRecord> steps =
        stepStore.findByExecutionIdOrdered(r.executionId());
    int total = steps.size();
    int completed =
        (int)
            steps.stream()
                .filter(
                    s ->
                        s.state() == StepState.SUCCEEDED
                            || s.state() == StepState.SKIPPED
                            || s.state() == StepState.FAILED)
                .count();
    String current =
        steps.stream()
            .filter(
                s -> s.state() == StepState.RUNNING || s.state() == StepState.WAITING_EXTERNAL)
            .map(ExecutionStepRecord::stepId)
            .findFirst()
            .orElse(null);
    String waitState =
        r.state() == ExecutionState.WAITING_EXTERNAL
            ? (r.activeWaitType() == null ? "WAITING" : r.activeWaitType())
            : null;
    String callbackState = null;
    CallbackOutboxStorePort outbox = outboxStore.getIfAvailable();
    if (outbox != null) {
      callbackState =
          outbox
              .findByExecutionId(r.executionId())
              .map(o -> o.state() == null ? null : o.state().name())
              .orElse(null);
    }
    String bundle = null;
    ExecutionGovernanceFixationStorePort fix = fixationStore.getIfAvailable();
    if (fix != null) {
      bundle =
          fix.findByExecutionId(r.executionId())
              .map(f -> f.governanceBundleRef())
              .orElse(null);
    }
    return new OperationalExecutionListItem(
        r.executionId(),
        redactId(r.correlationId()),
        r.routeCode() == null
            ? null
            : r.routeCode() + (r.routeVersion() == null ? "" : "@" + r.routeVersion()),
        r.routeCode(),
        r.state(),
        r.technicalStatus() == null ? TechnicalStatus.PENDING : r.technicalStatus(),
        current,
        completed,
        total,
        waitState,
        callbackState,
        bundle,
        r.startedAt(),
        r.lastUpdatedAt(),
        r.completedAt(),
        durationMs(r.startedAt(), r.completedAt() != null ? r.completedAt() : r.lastUpdatedAt()),
        null);
  }

  private static Long durationMs(Instant from, Instant to) {
    if (from == null || to == null) {
      return null;
    }
    return Duration.between(from, to).toMillis();
  }

  private static String redactId(String id) {
    if (id == null || id.length() < 8) {
      return id;
    }
    return id.substring(0, 4) + "…" + id.substring(id.length() - 4);
  }
}
