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
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.readmodel.ListOperationalExecutionsQuery;
import br.com.banco.spider.operational.readmodel.OperationalEventView;
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
  private OperationalEventStorePort operationalEventStore;
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

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setOperationalEventStore(OperationalEventStorePort store) {
    this.operationalEventStore = store;
  }

  public Mono<ListPage> list(ListOperationalExecutionsQuery query) {
    return Mono.fromCallable(() -> listBlocking(query)).subscribeOn(Schedulers.boundedElastic());
  }

  public Mono<Optional<OperationalExecutionDetail>> getDetail(String executionId) {
    return Mono.fromCallable(() -> Optional.ofNullable(detailBlocking(executionId)))
        .subscribeOn(Schedulers.boundedElastic());
  }

  public Mono<List<OperationalEventView>> listOperationalEvents(String executionId) {
    return Mono.fromCallable(
            () -> {
              if (operationalEventStore == null) {
                return List.<OperationalEventView>of();
              }
              return operationalEventStore.findByExecutionId(executionId).stream()
                  .map(
                      event ->
                          new OperationalEventView(
                              event.eventId(),
                              event.schemaVersion(),
                              event.eventType(),
                              event.category(),
                              event.occurredAt(),
                              event.executionId(),
                              event.interactionId(),
                              event.correlationId(),
                              event.source(),
                              event.outcome(),
                              event.durationMs(),
                              event.metadata()))
                  .toList();
            })
        .subscribeOn(Schedulers.boundedElastic());
  }

  private br.com.banco.spider.execution.route.RouteCatalogPort monitorRouteCatalog;
  private br.com.banco.spider.config.SatelliteContractProperties satelliteProperties;
  private br.com.banco.spider.config.SegSenseDemoProperties segsenseDemoProperties;
  private br.com.banco.spider.config.CreditDemoProperties creditDemoProperties;
  private org.springframework.core.env.Environment environment;

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setMonitorRouteCatalog(br.com.banco.spider.execution.route.RouteCatalogPort catalog) {
    this.monitorRouteCatalog = catalog;
  }

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setSatelliteProperties(br.com.banco.spider.config.SatelliteContractProperties properties) {
    this.satelliteProperties = properties;
  }

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setSegSenseDemoProperties(br.com.banco.spider.config.SegSenseDemoProperties properties) {
    this.segsenseDemoProperties = properties;
  }

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setCreditDemoProperties(br.com.banco.spider.config.CreditDemoProperties properties) {
    this.creditDemoProperties = properties;
  }

  @org.springframework.beans.factory.annotation.Autowired(required = false)
  void setEnvironment(org.springframework.core.env.Environment environment) {
    this.environment = environment;
  }

  private Mono<Map<String, Object>> withMonitorScenarios(Map<String, Object> body) {
    var operations = List.of("SUCCESS_MULTI_STEP", "RETRY_THEN_SUCCESS", "BUSINESS_NEGATIVE",
        "WAIT_SIGNAL_RESUME", "CALLBACK_RECONCILIATION", "TECHNICAL_FAILURE");
    return reactor.core.publisher.Flux.fromIterable(operations)
        .concatMap(operation -> monitorRouteCatalog == null ? Mono.<String>empty() :
            monitorRouteCatalog.findPublishedCandidates("journey:mock", "mock", operation)
                .filter(routes -> !routes.isEmpty()).map(routes -> operation))
        .collectList().map(available -> {
          var filtered = new java.util.ArrayList<>(available);
          if (filtered.contains("WAIT_SIGNAL_RESUME") && !signalHttpEnabled()) {
            filtered.remove("WAIT_SIGNAL_RESUME");
          }
          var result = new java.util.LinkedHashMap<String, Object>(body);
          result.put("availableScenarios", filtered);
          return result;
        });
  }

  public Mono<Map<String, Object>> simulationReadiness() {
    return Mono.fromCallable(this::evaluateSimulation).subscribeOn(Schedulers.boundedElastic());
  }

  private boolean signalHttpEnabled() {
    return environment != null
        && Boolean.parseBoolean(
            environment.getProperty("spider.canonical.signal-http.enabled", "false"));
  }

  private Map<String, Object> evaluateSimulation() {
    String segsenseUrl =
        segsenseDemoProperties != null && segsenseDemoProperties.getProductUrl() != null
            ? segsenseDemoProperties.getProductUrl()
            : "http://127.0.0.1:5178/demonstracao/mvp-integrado";
    String mockUrl =
        segsenseDemoProperties != null && segsenseDemoProperties.getMockBaseUrl() != null
            ? segsenseDemoProperties.getMockBaseUrl()
            : "http://127.0.0.1:8095";
    var segsenseMissing = new java.util.ArrayList<String>();
    boolean satelliteOn = satelliteProperties != null && satelliteProperties.isEnabled();
    var registry = satelliteProperties == null ? java.util.Map.<String, br.com.banco.spider.config.SatelliteContractProperties.SatelliteEntry>of() : satelliteProperties.getRegistry();
    var providers = satelliteProperties == null ? java.util.Map.<String, br.com.banco.spider.config.SatelliteContractProperties.ProviderEntry>of() : satelliteProperties.getProviders();
    var segsense = registry == null ? null : registry.get("segsense");
    var insurance = providers == null ? null : providers.get("insurance-provider-mock");
    if (!satelliteOn) {
      segsenseMissing.add("Contrato de satélite desligado neste ambiente");
    }
    if (segsense == null || !"ACTIVE".equalsIgnoreCase(segsense.getStatus())) {
      segsenseMissing.add("SegSense ausente ou inativo no registro");
    }
    if (insurance == null) {
      segsenseMissing.add("Provider mock de seguro não configurado");
    } else if (!reachable(joinUrl(mockUrl, "/health"))) {
      segsenseMissing.add("Provider mock de seguro não responde em " + mockUrl);
    }
    if (!reachable(segsenseUrl)) {
      segsenseMissing.add("Produto SegSense não responde em " + segsenseUrl);
    }
    var spiderbankMissing = new java.util.ArrayList<String>();
    String spiderbankUrl =
        creditDemoProperties != null && creditDemoProperties.getProductUrl() != null
            ? creditDemoProperties.getProductUrl()
            : "http://127.0.0.1:5190/";
    String creditMockUrl =
        creditDemoProperties != null && creditDemoProperties.getMockBaseUrl() != null
            ? creditDemoProperties.getMockBaseUrl()
            : "http://127.0.0.1:8096";
    var spiderbank = registry == null ? null : registry.get("spiderbank");
    var credit = providers == null ? null : providers.get("credit-provider-mock");
    if (!satelliteOn) {
      spiderbankMissing.add("Contrato de satélite desligado neste ambiente");
    }
    if (spiderbank == null || !"ACTIVE".equalsIgnoreCase(spiderbank.getStatus())) {
      spiderbankMissing.add("SpiderBank ausente ou inativo no registro");
    }
    if (creditDemoProperties == null || !creditDemoProperties.isEnabled()) {
      spiderbankMissing.add("Recorte demonstrativo de crédito desligado neste ambiente");
    } else if (creditDemoProperties.getAssertionSecret() == null
        || creditDemoProperties.getAssertionSecret().length() < 16) {
      spiderbankMissing.add("Afirmação de cliente sintético não configurada neste ambiente");
    }
    java.util.List<String> creditCapabilities =
        java.util.List.of(
            "GET_CUSTOMER_PROFILE",
            "CHECK_CUSTOMER_REGISTRATION",
            "GET_CREDIT_PROFILE",
            "FIND_ELIGIBLE_PRODUCTS",
            "SIMULATE_WORKING_CAPITAL");
    if (credit == null || !credit.getCapabilities().containsAll(creditCapabilities)) {
      spiderbankMissing.add("Provider mock de crédito não registrado para as capabilities demonstrativas");
    } else if (!reachable(joinUrl(creditMockUrl, "/health"))) {
      spiderbankMissing.add("Provider mock de crédito não responde em " + creditMockUrl);
    }
    String bffUrl =
        creditDemoProperties != null && creditDemoProperties.getBffUrl() != null
            ? creditDemoProperties.getBffUrl()
            : "http://127.0.0.1:8090/api/health";
    if (!reachable(bffUrl)) {
      spiderbankMissing.add("BFF do SpiderBank não responde em " + bffUrl);
    }
    if (!reachable(spiderbankUrl)) {
      spiderbankMissing.add("Produto SpiderBank não responde em " + spiderbankUrl);
    }
    return Map.of(
        "signalHttpEnabled",
        signalHttpEnabled(),
        "satellites",
        List.of(
            Map.of(
                "id",
                "segsense",
                "available",
                segsenseMissing.isEmpty(),
                "missing",
                List.copyOf(segsenseMissing),
                "url",
                segsenseUrl),
            Map.of(
                "id",
                "spiderbank",
                "available",
                spiderbankMissing.isEmpty(),
                "missing",
                List.copyOf(spiderbankMissing),
                "url",
                spiderbankUrl)));
  }

  private static String joinUrl(String base, String path) {
    if (base == null || base.isBlank()) {
      return path;
    }
    return base.endsWith("/") ? base.substring(0, base.length() - 1) + path : base + path;
  }

  private static boolean reachable(String url) {
    if (url == null || url.isBlank()) {
      return false;
    }
    try {
      var client =
          java.net.http.HttpClient.newBuilder()
              .version(java.net.http.HttpClient.Version.HTTP_1_1)
              .connectTimeout(java.time.Duration.ofSeconds(2))
              .build();
      var request =
          java.net.http.HttpRequest.newBuilder(java.net.URI.create(url))
              .timeout(java.time.Duration.ofSeconds(2))
              .header("Accept", "*/*")
              .GET()
              .build();
      var response = client.send(request, java.net.http.HttpResponse.BodyHandlers.discarding());
      return response.statusCode() >= 200 && response.statusCode() < 400;
    } catch (Exception ignored) {
      return false;
    }
  }

  public Mono<Map<String, Object>> monitorEvents() {
    return Mono.fromCallable(() -> {
      Instant to = Instant.now();
      Instant from = to.minus(Duration.ofHours(24));
      if (operationalEventStore == null) {
        return Map.<String, Object>of("available", false, "items", List.of(), "from", from, "to", to, "truncated", false);
      }
      var events = operationalEventStore.findRecentBetween(from, to, 2001);
      return Map.<String, Object>of("available", true, "items", events.stream().limit(2000).toList(),
          "from", from, "to", to, "truncated", events.size() > 2000);
    }).subscribeOn(Schedulers.boundedElastic()).flatMap(this::withMonitorScenarios);
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
