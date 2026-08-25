package br.com.banco.spider.operational.failurelab;

import br.com.banco.spider.canonical.contract.TraceDescriptor;
import br.com.banco.spider.config.FailureLabProperties;
import br.com.banco.spider.execution.domain.CanonicalOutcome;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.signal.ExecutionResumeService;
import br.com.banco.spider.execution.signal.ExternalSignalEnvelope;
import br.com.banco.spider.execution.signal.ExternalSignalIngressOutcome;
import br.com.banco.spider.execution.signal.ExternalSignalIngressUseCase;
import br.com.banco.spider.execution.signal.SignalCompletion;
import br.com.banco.spider.execution.signal.SignalSecurityContext;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.integration.binding.ConfiguredAdapterBindingResolver;
import br.com.banco.spider.integration.port.AdapterDispositionMode;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.ObjectProvider;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Coordena uma execução controlada: submete o cenário ao mock, observa as fontes canônicas e
 * conclui com veredito e evidência. Nunca decide nada dentro da Engine.
 */
public class FailureLabOrchestrator {

  private static final Logger log = LoggerFactory.getLogger(FailureLabOrchestrator.class);

  private static final String SIGNAL_CONTRACT_VERSION = "1.0";
  private static final String UNTRUSTED_PRINCIPAL_REF = "principal:failure-lab-untrusted";
  private static final Set<ExternalSignalIngressOutcome> SECURITY_REJECTIONS =
      EnumSet.of(
          ExternalSignalIngressOutcome.UNAUTHORIZED,
          ExternalSignalIngressOutcome.INVALID_PROOF,
          ExternalSignalIngressOutcome.REPLAY_CONFLICT,
          ExternalSignalIngressOutcome.REJECTED);

  private final FailureLabProperties properties;
  private final FailureLabCatalogLoader catalog;
  private final FailureLabRunStorePort store;
  private final FailureLabSubmitSupport submitSupport;
  private final FailureLabObservationVerifier verifier;
  private final FailureLabEvidenceService evidenceService;
  private final SpiderClock clock;
  private final IdentifierGenerator ids;
  private final ObjectProvider<ExecutionWaitStorePort> waitProvider;
  private final ObjectProvider<ExecutionResumeService> resumeProvider;
  private final ObjectProvider<ExternalSignalIngressUseCase> signalIngressProvider;

  public FailureLabOrchestrator(
      FailureLabProperties properties,
      FailureLabCatalogLoader catalog,
      FailureLabRunStorePort store,
      FailureLabSubmitSupport submitSupport,
      FailureLabObservationVerifier verifier,
      FailureLabEvidenceService evidenceService,
      SpiderClock clock,
      IdentifierGenerator ids,
      ObjectProvider<ExecutionWaitStorePort> waitProvider,
      ObjectProvider<ExecutionResumeService> resumeProvider,
      ObjectProvider<ExternalSignalIngressUseCase> signalIngressProvider) {
    this.properties = properties;
    this.catalog = catalog;
    this.store = store;
    this.submitSupport = submitSupport;
    this.verifier = verifier;
    this.evidenceService = evidenceService;
    this.clock = clock;
    this.ids = ids;
    this.waitProvider = waitProvider;
    this.resumeProvider = resumeProvider;
    this.signalIngressProvider = signalIngressProvider;
  }

  private record Dispatch(List<String> executionRefs, Map<String, String> safeFacts) {
    static Dispatch of(String executionId) {
      return new Dispatch(List.of(executionId), Map.of());
    }

    static Dispatch empty() {
      return new Dispatch(List.of(), Map.of());
    }
  }

  public Mono<FailureLabRun> startRun(
      String scenarioCode,
      String scenarioVersion,
      Map<String, String> parameters,
      String requestedBy) {
    return Mono.<FailureLabRun>defer(
        () -> {
          if (!properties.isEnabled()) {
            return Mono.error(new FailureLabRejectedException(FailureLabRejectedException.DISABLED));
          }
          FailureScenarioDefinition scenario =
              catalog
                  .findScenario(scenarioCode, scenarioVersion)
                  .orElseThrow(
                      () ->
                          new FailureLabRejectedException(
                              FailureLabRejectedException.SCENARIO_NOT_FOUND));
          Map<String, String> safeParameters = validateParameters(scenario, parameters);
          rejectIfBusy();

          String labRunId = ids.nextId("labrun");
          Instant requestedAt = clock.now();
          FailureLabRun requested =
              FailureLabRun.requested(labRunId, scenario, safeParameters, requestedBy, requestedAt);
          store.save(requested);

          FailureLabRun running = requested.started(clock.now());
          store.save(running);
          log.info(
              "event=failure_lab_run_started labRunId={} scenarioRef={} boundary={}",
              labRunId,
              scenario.ref(),
              scenario.targetBoundary());

          return dispatch(scenario, labRunId)
              .timeout(effectiveTimeout(scenario))
              .flatMap(result -> complete(running, scenario, result))
              .onErrorResume(
                  java.util.concurrent.TimeoutException.class,
                  timeout -> Mono.just(terminate(running, FailureLabRunStatus.TIMED_OUT, "RUN_TIMEOUT")))
              .onErrorResume(
                  failure ->
                      Mono.just(
                          terminate(
                              running,
                              FailureLabRunStatus.FAILED,
                              failure.getClass().getSimpleName())));
        });
  }

  private Mono<Dispatch> dispatch(FailureScenarioDefinition scenario, String labRunId) {
    return switch (scenario.code()) {
      case "INSUFFICIENT_SAMPLE" -> Mono.just(Dispatch.empty());
      case "OPERATIONAL_DEGRADATION" -> repeatedSubmit(scenario, labRunId);
      case "WAIT_AND_RESUME" -> waitAndResume(scenario, labRunId);
      case "SIGNAL_SECURITY_REJECTED" -> signalSecurityRejected(scenario, labRunId);
      default -> singleSubmit(scenario, labRunId);
    };
  }

  private Mono<Dispatch> singleSubmit(FailureScenarioDefinition scenario, String labRunId) {
    if (!scenario.requiresEngineSubmission()) {
      return Mono.just(Dispatch.empty());
    }
    return submitSupport.submit(scenario, labRunId).map(outcome -> Dispatch.of(outcome.executionId()));
  }

  private Mono<Dispatch> repeatedSubmit(FailureScenarioDefinition scenario, String labRunId) {
    if (!scenario.requiresEngineSubmission()) {
      return Mono.just(Dispatch.empty());
    }
    int executions =
        Math.max(
            1, Math.min(scenario.maximumExecutions(), properties.getMaxExecutionsPerRun()));
    return Flux.range(0, executions)
        .concatMap(index -> submitSupport.submit(scenario, labRunId))
        .map(FailureLabSubmitSupport.SubmitOutcome::executionId)
        .collectList()
        .map(refs -> new Dispatch(List.copyOf(refs), Map.of()));
  }

  private Mono<Dispatch> waitAndResume(FailureScenarioDefinition scenario, String labRunId) {
    return submitSupport
        .submit(scenario, labRunId)
        .flatMap(
            outcome -> {
              List<String> refs = List.of(outcome.executionId());
              ExecutionResumeService resume = resumeProvider.getIfAvailable();
              Optional<ExecutionWaitRecord> wait = activeWait(outcome.executionId());
              if (resume == null || wait.isEmpty()) {
                return Mono.just(
                    new Dispatch(
                        refs,
                        Map.of(
                            "resumeOutcome",
                            resume == null ? "RESUME_UNAVAILABLE" : "NO_ACTIVE_WAIT")));
              }
              return resume
                  .applySignalAndResume(completionSignal(wait.get(), labRunId), wait.get())
                  .map(
                      resumed ->
                          new Dispatch(
                              refs,
                              Map.of(
                                  "resumeOutcome",
                                  FailureLabRedaction.safeReason(resumed.status().name()))))
                  .onErrorResume(
                      failure ->
                          Mono.just(
                              new Dispatch(refs, Map.of("resumeOutcome", "RESUME_FAILED"))));
            });
  }

  private Mono<Dispatch> signalSecurityRejected(
      FailureScenarioDefinition scenario, String labRunId) {
    return submitSupport
        .submit(scenario, labRunId)
        .flatMap(
            outcome -> {
              List<String> refs = List.of(outcome.executionId());
              ExternalSignalIngressUseCase ingress = signalIngressProvider.getIfAvailable();
              Optional<ExecutionWaitRecord> wait = activeWait(outcome.executionId());
              if (ingress == null || wait.isEmpty()) {
                return Mono.just(
                    new Dispatch(
                        refs,
                        Map.of(
                            "signalOutcome",
                            ingress == null ? "INGRESS_UNAVAILABLE" : "NO_ACTIVE_WAIT")));
              }
              return ingress
                  .ingest(untrustedSignal(wait.get(), labRunId))
                  .map(result -> new Dispatch(refs, signalFacts(result.outcome())))
                  .onErrorResume(
                      failure ->
                          Mono.just(
                              new Dispatch(
                                  refs,
                                  Map.of(
                                      "signalOutcome",
                                      "INGRESS_FAILED",
                                      "signalCategory",
                                      "SECURITY"))));
            });
  }

  private static Map<String, String> signalFacts(ExternalSignalIngressOutcome outcome) {
    Map<String, String> facts = new LinkedHashMap<>();
    facts.put("signalOutcome", FailureLabRedaction.safeReason(outcome.name()));
    if (SECURITY_REJECTIONS.contains(outcome)) {
      facts.put("signalCategory", "SECURITY");
    }
    return Map.copyOf(facts);
  }

  private Optional<ExecutionWaitRecord> activeWait(String executionId) {
    ExecutionWaitStorePort waits = waitProvider.getIfAvailable();
    if (waits == null) {
      return Optional.empty();
    }
    return waits.findByExecutionId(executionId).stream()
        .filter(wait -> wait.state() == WaitState.WAITING)
        .findFirst();
  }

  private ExternalSignalEnvelope completionSignal(ExecutionWaitRecord wait, String labRunId) {
    Instant now = clock.now();
    String correlationId = "corr-lab-" + labRunId;
    String sourceRef = sourceRefFor(wait);
    return new ExternalSignalEnvelope(
        SIGNAL_CONTRACT_VERSION,
        ids.nextId("labsig"),
        sourceRef,
        ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
        wait.expectedSignalContractRef(),
        wait.executionId(),
        wait.stepId(),
        wait.externalOperationRef(),
        now,
        now,
        correlationId,
        new TraceDescriptor(correlationId, FailureLabSubmitSupport.newTraceparent(), null),
        new SignalSecurityContext(
            "principal:failure-lab",
            sourceRef,
            "MOCK",
            now.minusSeconds(1),
            now.plus(Duration.ofMinutes(5)),
            wait.integrityProfileRef() == null
                ? "profile:signal:test@1.0"
                : wait.integrityProfileRef(),
            null),
        new SignalCompletion(
            AdapterDispositionMode.COMPLETED,
            CanonicalOutcome.technical(TechnicalStatus.SUCCESS),
            List.of(),
            List.of()));
  }

  /** Sinal com contexto de segurança expirado — a recusa é o comportamento esperado. */
  private ExternalSignalEnvelope untrustedSignal(ExecutionWaitRecord wait, String labRunId) {
    Instant now = clock.now();
    String correlationId = "corr-lab-" + labRunId;
    String sourceRef = sourceRefFor(wait);
    return new ExternalSignalEnvelope(
        SIGNAL_CONTRACT_VERSION,
        ids.nextId("labsig"),
        sourceRef,
        ConfiguredAdapterBindingResolver.DEFAULT_MOCK_BINDING,
        wait.expectedSignalContractRef(),
        wait.executionId(),
        wait.stepId(),
        wait.externalOperationRef(),
        now,
        now,
        correlationId,
        new TraceDescriptor(correlationId, FailureLabSubmitSupport.newTraceparent(), null),
        new SignalSecurityContext(
            UNTRUSTED_PRINCIPAL_REF,
            sourceRef,
            "NONE",
            now.minus(Duration.ofHours(2)),
            now.minus(Duration.ofHours(1)),
            "profile:signal:failure-lab-untrusted@1.0",
            null),
        new SignalCompletion(
            AdapterDispositionMode.COMPLETED,
            CanonicalOutcome.technical(TechnicalStatus.SUCCESS),
            List.of(),
            List.of()));
  }

  private static String sourceRefFor(ExecutionWaitRecord wait) {
    return wait.expectedSourceRef() == null
        ? FailureLabRouteSupport.MOCK_ASYNC_SOURCE_REF
        : wait.expectedSourceRef();
  }

  private Mono<FailureLabRun> complete(
      FailureLabRun running, FailureScenarioDefinition scenario, Dispatch dispatch) {
    return Mono.fromCallable(
        () -> {
          FailureLabRun observing =
              running
                  .withExecutionRefs(dispatch.executionRefs())
                  .withStatus(FailureLabRunStatus.OBSERVING);
          store.save(observing);

          List<VerificationResult> results =
              verifier.verify(observing, scenario, dispatch.safeFacts());
          FailureLabRunStatus finalStatus = decide(scenario, results);
          FailureLabRun verified =
              observing.completed(finalStatus, clock.now(), results, summarize(results), null);

          if (properties.getEvidence().isEnabled()) {
            FailureLabEvidenceBundle bundle = evidenceService.build(verified, scenario);
            store.saveEvidence(bundle);
          }
          store.save(verified);
          log.info(
              "event=failure_lab_run_completed labRunId={} scenarioRef={} status={}",
              verified.labRunId(),
              scenario.ref(),
              finalStatus);
          return verified;
        });
  }

  private FailureLabRun terminate(
      FailureLabRun running, FailureLabRunStatus status, String reasonCode) {
    String safeReason = FailureLabRedaction.safeReason(reasonCode);
    FailureLabRun terminated =
        running.completed(status, clock.now(), running.verificationResults(), null, safeReason);
    store.save(terminated);
    log.info(
        "event=failure_lab_run_terminated labRunId={} status={} reasonCode={}",
        terminated.labRunId(),
        status,
        safeReason);
    return terminated;
  }

  static FailureLabRunStatus decide(
      FailureScenarioDefinition scenario, List<VerificationResult> results) {
    Map<String, ExpectedObservation> required = new LinkedHashMap<>();
    for (ExpectedObservation observation : scenario.expectedObservations()) {
      if (observation.required()) {
        required.put(observation.code(), observation);
      }
    }
    boolean anyRequiredFailed = false;
    boolean allRequiredPassed = true;
    for (VerificationResult result : results) {
      if (!required.containsKey(result.observationCode())) {
        continue;
      }
      if (result.status() == VerificationStatus.FAILED) {
        anyRequiredFailed = true;
      }
      if (result.status() != VerificationStatus.PASSED) {
        allRequiredPassed = false;
      }
    }
    if (anyRequiredFailed) {
      return FailureLabRunStatus.FAILED;
    }
    return allRequiredPassed && !required.isEmpty()
        ? FailureLabRunStatus.VERIFIED
        : FailureLabRunStatus.INCONCLUSIVE;
  }

  private static String summarize(List<VerificationResult> results) {
    List<String> parts = new ArrayList<>();
    for (VerificationStatus status : VerificationStatus.values()) {
      long count = results.stream().filter(result -> result.status() == status).count();
      if (count > 0) {
        parts.add(status.name() + "=" + count);
      }
    }
    return String.join(" ", parts);
  }

  private Duration effectiveTimeout(FailureScenarioDefinition scenario) {
    Duration configured = properties.getMaxRunDuration();
    Duration declared = scenario.maximumDuration();
    return configured.compareTo(declared) < 0 ? configured : declared;
  }

  private void rejectIfBusy() {
    long active =
        store.listRecent(properties.getMaxConcurrentRuns() * 10 + 10).stream()
            .filter(run -> run.status().isActive())
            .count();
    if (active >= properties.getMaxConcurrentRuns()) {
      throw new FailureLabRejectedException(FailureLabRejectedException.CONCURRENCY_LIMIT_REACHED);
    }
  }

  private static Map<String, String> validateParameters(
      FailureScenarioDefinition scenario, Map<String, String> parameters) {
    if (parameters == null || parameters.isEmpty()) {
      return Map.of();
    }
    for (String key : parameters.keySet()) {
      if (!scenario.allowedParameterKeys().contains(key)) {
        throw new FailureLabRejectedException(FailureLabRejectedException.PARAMETER_NOT_ALLOWED);
      }
    }
    return FailureLabRedaction.sanitize(parameters);
  }
}
