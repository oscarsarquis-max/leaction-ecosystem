package br.com.banco.spider.operational.failurelab;

import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.execution.wait.WaitState;
import br.com.banco.spider.operational.capacity.AdmissionResult;
import br.com.banco.spider.operational.capacity.CircuitPhase;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventCategory;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.health.HealthDimensionStatus;
import br.com.banco.spider.operational.health.OperationalHealthQueryService;
import br.com.banco.spider.operational.health.OperationalHealthSnapshot;
import br.com.banco.spider.operational.health.SliResult;
import br.com.banco.spider.operational.health.SloEvaluation;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Avalia as observações declaradas contra as fontes canônicas. Ausência de evidência para uma
 * observação obrigatória resulta em NOT_OBSERVED — nunca em PASSED.
 */
public class FailureLabObservationVerifier {

  private static final String HEALTH_WINDOW = "PT24H";
  private static final String ENTRY_STEP_ID = "step-1";
  private static final String FENCING_UNCHANGED = "UNCHANGED";

  private final SpiderClock clock;
  private final ObjectProvider<ExecutionControlStorePort> controlProvider;
  private final ObjectProvider<StepAttemptStorePort> attemptProvider;
  private final ObjectProvider<ExecutionWaitStorePort> waitProvider;
  private final ObjectProvider<OperationalEventStorePort> eventProvider;
  private final ObjectProvider<CallbackOutboxStorePort> callbackProvider;
  private final ObjectProvider<OperationalHealthQueryService> healthProvider;

  public FailureLabObservationVerifier(
      SpiderClock clock,
      ObjectProvider<ExecutionControlStorePort> controlProvider,
      ObjectProvider<StepAttemptStorePort> attemptProvider,
      ObjectProvider<ExecutionWaitStorePort> waitProvider,
      ObjectProvider<OperationalEventStorePort> eventProvider,
      ObjectProvider<CallbackOutboxStorePort> callbackProvider,
      ObjectProvider<OperationalHealthQueryService> healthProvider) {
    this.clock = clock;
    this.controlProvider = controlProvider;
    this.attemptProvider = attemptProvider;
    this.waitProvider = waitProvider;
    this.eventProvider = eventProvider;
    this.callbackProvider = callbackProvider;
    this.healthProvider = healthProvider;
  }

  public List<VerificationResult> verify(
      FailureLabRun run, FailureScenarioDefinition scenario, Map<String, String> safeRuntimeFacts) {
    Map<String, String> facts =
        safeRuntimeFacts == null ? Map.of() : FailureLabRedaction.sanitize(safeRuntimeFacts);
    HealthLookup health = new HealthLookup(healthProvider);
    List<VerificationResult> results = new ArrayList<>();
    // NO_SECRET_EXPOSED inspeciona o material já produzido, por isso é avaliado por último.
    List<ExpectedObservation> ordered = new ArrayList<>();
    List<ExpectedObservation> deferred = new ArrayList<>();
    for (ExpectedObservation observation : scenario.expectedObservations()) {
      if (observation.predicateType() == ObservationPredicateType.NO_SECRET_EXPOSED) {
        deferred.add(observation);
      } else {
        ordered.add(observation);
      }
    }
    ordered.addAll(deferred);
    for (ExpectedObservation observation : ordered) {
      results.add(evaluate(run, observation, facts, health, results));
    }
    return List.copyOf(results);
  }

  private VerificationResult evaluate(
      FailureLabRun run,
      ExpectedObservation observation,
      Map<String, String> facts,
      HealthLookup health,
      List<VerificationResult> accumulated) {
    try {
      return switch (observation.predicateType()) {
        case EXECUTION_REACHED_STATE -> executionReachedState(run, observation);
        case OPERATIONAL_EVENT_EMITTED -> operationalEventEmitted(run, observation);
        case WAIT_OPENED -> waitOpened(run, observation);
        case WAIT_RESUMED -> waitResumed(run, observation);
        case ATTEMPT_COUNT_AT_LEAST -> attemptCountAtLeast(run, observation);
        case CALLBACK_REACHED_STATUS -> callbackReachedStatus(run, observation);
        case SIGNAL_REJECTED_WITH_CATEGORY -> signalRejected(run, observation, facts);
        case HEALTH_DIMENSION_REACHED_STATUS -> healthDimension(observation, health);
        case SLO_EVALUATION_REACHED_STATUS -> sloStatus(observation, health);
        case SLI_STATUS_EQUALS -> sliStatus(observation, health);
        case HEALTH_OVERALL_STATUS -> healthOverall(observation, health);
        case NO_SECRET_EXPOSED -> noSecretExposed(run, observation, accumulated);
        case WORKER_FACT_EQUALS -> workerFact(observation, facts);
        case ADMISSION_RESULT_EQUALS -> admissionResult(observation, facts);
        case CIRCUIT_PHASE_EQUALS -> circuitPhase(observation, facts);
        case FENCING_TOKEN_UNCHANGED -> fencingTokenUnchanged(observation, facts);
      };
    } catch (RuntimeException failure) {
      return result(
          observation,
          VerificationStatus.INCONCLUSIVE,
          "",
          Map.of("reasonCode", FailureLabRedaction.safeReason(failure.getClass().getSimpleName())),
          "Não foi possível avaliar a observação com as fontes disponíveis.");
    }
  }

  private VerificationResult executionReachedState(
      FailureLabRun run, ExpectedObservation observation) {
    ExecutionControlStorePort store = controlProvider.getIfAvailable();
    if (store == null) {
      return notApplicable(observation, "executionControlStore");
    }
    List<ExecutionControlRecord> records = controls(run, store);
    if (records.isEmpty()) {
      return notObserved(observation, "Nenhum registro de controle encontrado para a execução.");
    }
    String expected = observation.expectedValue().toUpperCase(Locale.ROOT);
    Optional<ExecutionControlRecord> match =
        records.stream().filter(record -> record.state().name().equals(expected)).findFirst();
    String observed =
        String.join(",", records.stream().map(record -> record.state().name()).toList());
    if (match.isPresent()) {
      return result(
          observation,
          VerificationStatus.PASSED,
          observed,
          Map.of("executionRefCount", String.valueOf(records.size())),
          "Estado esperado observado no controle de execução.");
    }
    return result(
        observation,
        VerificationStatus.FAILED,
        observed,
        Map.of("executionRefCount", String.valueOf(records.size())),
        "Estado observado difere do estado esperado.");
  }

  private VerificationResult operationalEventEmitted(
      FailureLabRun run, ExpectedObservation observation) {
    OperationalEventStorePort store = eventProvider.getIfAvailable();
    if (store == null) {
      return notApplicable(observation, "operationalEventStore");
    }
    String expected = observation.expectedValue().toUpperCase(Locale.ROOT);
    for (String executionId : run.executionRefs()) {
      for (OperationalEvent event : store.findByExecutionId(executionId)) {
        if (event.eventType().name().equals(expected)) {
          return result(
              observation,
              VerificationStatus.PASSED,
              event.eventType().name(),
              Map.of("eventCategory", event.category().name()),
              "Evento operacional esperado encontrado.");
        }
      }
    }
    return notObserved(observation, "Nenhum evento operacional do tipo esperado foi registrado.");
  }

  private VerificationResult waitOpened(FailureLabRun run, ExpectedObservation observation) {
    ExecutionWaitStorePort store = waitProvider.getIfAvailable();
    if (store == null) {
      return notApplicable(observation, "executionWaitStore");
    }
    List<ExecutionWaitRecord> waits = waits(run, store);
    if (waits.isEmpty()) {
      return notObserved(observation, "Nenhuma espera foi registrada para a execução.");
    }
    return result(
        observation,
        VerificationStatus.PASSED,
        waits.getFirst().waitType().name(),
        Map.of("waitCount", String.valueOf(waits.size())),
        "Espera aberta encontrada para a execução.");
  }

  private VerificationResult waitResumed(FailureLabRun run, ExpectedObservation observation) {
    ExecutionWaitStorePort store = waitProvider.getIfAvailable();
    if (store == null) {
      return notApplicable(observation, "executionWaitStore");
    }
    List<ExecutionWaitRecord> waits = waits(run, store);
    if (waits.isEmpty()) {
      return notObserved(observation, "Nenhuma espera foi registrada para a execução.");
    }
    Optional<ExecutionWaitRecord> resumed =
        waits.stream().filter(wait -> wait.state() == WaitState.RESUMED).findFirst();
    if (resumed.isPresent()) {
      return result(
          observation,
          VerificationStatus.PASSED,
          WaitState.RESUMED.name(),
          Map.of(
              "resolutionReasonCode",
              FailureLabRedaction.safeReason(resumed.get().resolutionReasonCode())),
          "Espera resolvida por sinal aplicado.");
    }
    return notObserved(
        observation,
        "A espera permanece sem resolução: estado atual " + waits.getFirst().state().name() + ".");
  }

  private VerificationResult attemptCountAtLeast(
      FailureLabRun run, ExpectedObservation observation) {
    StepAttemptStorePort store = attemptProvider.getIfAvailable();
    if (store == null) {
      return notApplicable(observation, "stepAttemptStore");
    }
    int expected = parseInt(observation.expectedValue(), 1);
    int best = 0;
    for (String executionId : run.executionRefs()) {
      List<StepAttemptRecord> attempts = store.findByExecutionAndStep(executionId, ENTRY_STEP_ID);
      best = Math.max(best, attempts.size());
    }
    if (best == 0) {
      return notObserved(observation, "Nenhuma tentativa registrada para o passo de entrada.");
    }
    VerificationStatus status =
        best >= expected ? VerificationStatus.PASSED : VerificationStatus.FAILED;
    return result(
        observation,
        status,
        String.valueOf(best),
        Map.of("stepRef", ENTRY_STEP_ID),
        status == VerificationStatus.PASSED
            ? "Número de tentativas atende ao mínimo esperado."
            : "Número de tentativas abaixo do mínimo esperado.");
  }

  private VerificationResult callbackReachedStatus(
      FailureLabRun run, ExpectedObservation observation) {
    CallbackOutboxStorePort store = callbackProvider.getIfAvailable();
    if (store == null) {
      return notApplicable(observation, "callbackOutboxStore");
    }
    String expected = observation.expectedValue().toUpperCase(Locale.ROOT);
    for (String executionId : run.executionRefs()) {
      Optional<CallbackOutboxRecord> record = store.findByExecutionId(executionId);
      if (record.isEmpty()) {
        continue;
      }
      String observed = record.get().state().name();
      if (observed.equals(expected)) {
        return result(
            observation,
            VerificationStatus.PASSED,
            observed,
            Map.of(),
            "Callback atingiu o estado esperado.");
      }
      return result(
          observation,
          VerificationStatus.FAILED,
          observed,
          Map.of(),
          "Callback registrado em estado diferente do esperado.");
    }
    return notObserved(observation, "Nenhum callback registrado para a execução.");
  }

  private VerificationResult signalRejected(
      FailureLabRun run, ExpectedObservation observation, Map<String, String> facts) {
    String expected = observation.expectedValue().toUpperCase(Locale.ROOT);
    OperationalEventStorePort store = eventProvider.getIfAvailable();
    if (store != null) {
      for (String executionId : run.executionRefs()) {
        for (OperationalEvent event : store.findByExecutionId(executionId)) {
          boolean securityRejection =
              event.category() == OperationalEventCategory.SECURITY
                  || event.eventType().name().equals("SIGNAL_REJECTED");
          if (securityRejection
              && (expected.isEmpty()
                  || event.category().name().equals(expected)
                  || event.eventType().name().contains(expected))) {
            return result(
                observation,
                VerificationStatus.PASSED,
                event.eventType().name(),
                Map.of("eventCategory", event.category().name()),
                "Recusa de sinal registrada na telemetria operacional.");
          }
        }
      }
    }
    String outcome = facts.get("signalOutcome");
    String category = facts.get("signalCategory");
    if (outcome != null && category != null && category.equals(expected)) {
      return result(
          observation,
          VerificationStatus.PASSED,
          outcome,
          Map.of("reasonCode", FailureLabRedaction.safeReason(outcome)),
          "Recusa de sinal confirmada pelo desfecho seguro da ingestão.");
    }
    if (outcome != null) {
      return result(
          observation,
          VerificationStatus.INCONCLUSIVE,
          outcome,
          Map.of("reasonCode", FailureLabRedaction.safeReason(outcome)),
          "Sinal recusado, mas sem categoria de segurança comprovável nesta configuração.");
    }
    return notObserved(observation, "Nenhuma recusa de sinal foi registrada.");
  }

  private VerificationResult healthDimension(ExpectedObservation observation, HealthLookup health) {
    OperationalHealthSnapshot snapshot = health.snapshot();
    if (snapshot == null) {
      return healthUnavailable(observation, health);
    }
    String[] parts = splitExpected(observation.expectedValue());
    String dimension = parts[0];
    String expectedStatus = parts[1];
    List<HealthDimensionStatus> dimensions = snapshot.dimensions();
    if (dimensions.isEmpty()) {
      return notObserved(observation, "Nenhuma dimensão operacional disponível na janela.");
    }
    for (HealthDimensionStatus status : dimensions) {
      boolean dimensionMatches = dimension == null || status.dimension().name().equals(dimension);
      if (dimensionMatches && status.status().name().equals(expectedStatus)) {
        return result(
            observation,
            VerificationStatus.PASSED,
            status.dimension().name() + ":" + status.status().name(),
            Map.of("healthWindow", HEALTH_WINDOW),
            "Dimensão operacional atingiu o estado esperado.");
      }
    }
    String observed =
        String.join(
            ",",
            dimensions.stream()
                .filter(status -> dimension == null || status.dimension().name().equals(dimension))
                .map(status -> status.dimension().name() + ":" + status.status().name())
                .toList());
    return inconclusiveHealth(observation, observed);
  }

  private VerificationResult sloStatus(ExpectedObservation observation, HealthLookup health) {
    OperationalHealthSnapshot snapshot = health.snapshot();
    if (snapshot == null) {
      return healthUnavailable(observation, health);
    }
    String[] parts = splitExpected(observation.expectedValue());
    String objective = parts[0];
    String expectedStatus = parts[1];
    List<SloEvaluation> evaluations = snapshot.sloEvaluations();
    if (evaluations.isEmpty()) {
      return notObserved(observation, "Nenhum objetivo operacional avaliado na janela.");
    }
    for (SloEvaluation evaluation : evaluations) {
      boolean codeMatches = objective == null || objective.equals(evaluation.objectiveCode());
      if (codeMatches && evaluation.status().name().equals(expectedStatus)) {
        return result(
            observation,
            VerificationStatus.PASSED,
            evaluation.objectiveCode() + ":" + evaluation.status().name(),
            Map.of("healthWindow", HEALTH_WINDOW),
            "Objetivo operacional atingiu o estado esperado.");
      }
    }
    String observed =
        String.join(
            ",",
            evaluations.stream()
                .map(evaluation -> evaluation.objectiveCode() + ":" + evaluation.status().name())
                .toList());
    return inconclusiveHealth(observation, observed);
  }

  private VerificationResult sliStatus(ExpectedObservation observation, HealthLookup health) {
    OperationalHealthSnapshot snapshot = health.snapshot();
    if (snapshot == null) {
      return healthUnavailable(observation, health);
    }
    String[] parts = splitExpected(observation.expectedValue());
    String sliCode = parts[0];
    String expectedStatus = parts[1];
    List<SliResult> slis = snapshot.slis();
    if (slis.isEmpty()) {
      return notObserved(observation, "Nenhum indicador operacional disponível na janela.");
    }
    for (SliResult sli : slis) {
      boolean codeMatches = sliCode == null || sliCode.equals(sli.code());
      if (codeMatches && sli.status().name().equals(expectedStatus)) {
        return result(
            observation,
            VerificationStatus.PASSED,
            sli.code() + ":" + sli.status().name(),
            Map.of("healthWindow", HEALTH_WINDOW),
            "Indicador operacional no estado esperado.");
      }
    }
    String observed =
        String.join(",", slis.stream().map(sli -> sli.code() + ":" + sli.status().name()).toList());
    return inconclusiveHealth(observation, observed);
  }

  private VerificationResult healthOverall(ExpectedObservation observation, HealthLookup health) {
    OperationalHealthSnapshot snapshot = health.snapshot();
    if (snapshot == null) {
      return healthUnavailable(observation, health);
    }
    String expected = observation.expectedValue().toUpperCase(Locale.ROOT);
    String observed = snapshot.overallStatus().name();
    if (observed.equals(expected)) {
      return result(
          observation,
          VerificationStatus.PASSED,
          observed,
          Map.of("healthWindow", HEALTH_WINDOW),
          "Leitura consolidada no estado esperado.");
    }
    return inconclusiveHealth(observation, observed);
  }

  /**
   * Compara um fato seguro publicado pelo harness do runtime, no formato {@code chave:VALOR}. Sem o
   * fato correspondente a observação é NOT_OBSERVED — nunca PASSED por omissão.
   */
  private VerificationResult workerFact(
      ExpectedObservation observation, Map<String, String> facts) {
    String raw = observation.expectedValue() == null ? "" : observation.expectedValue().trim();
    int separator = raw.indexOf(':');
    if (separator <= 0) {
      return notObserved(observation, "Observação do runtime sem chave de fato declarada.");
    }
    String key = raw.substring(0, separator);
    String expected = raw.substring(separator + 1);
    String observed = facts.get(key);
    if (observed == null) {
      return notObserved(observation, "O runtime de workers não publicou o fato esperado.");
    }
    if (observed.equals(expected)) {
      return result(
          observation,
          VerificationStatus.PASSED,
          observed,
          Map.of("reasonCode", FailureLabRedaction.safeReason(observed)),
          "O runtime de workers confirmou o comportamento esperado.");
    }
    return result(
        observation,
        VerificationStatus.INCONCLUSIVE,
        observed,
        Map.of("reasonCode", FailureLabRedaction.safeReason(observed)),
        "O runtime respondeu com desfecho diferente do declarado no cenário.");
  }

  /**
   * Desfecho de admissão publicado pelo governo de capacidade, no formato {@code chave:RESULTADO}. O
   * valor esperado precisa pertencer ao conjunto fechado de {@link AdmissionResult} — um cenário que
   * declare um desfecho inexistente é inconclusivo, não aprovado.
   */
  private VerificationResult admissionResult(
      ExpectedObservation observation, Map<String, String> facts) {
    return closedEnumFact(
        observation,
        facts,
        expected -> {
          try {
            AdmissionResult.valueOf(expected);
            return true;
          } catch (IllegalArgumentException unknown) {
            return false;
          }
        },
        "desfecho de admissão");
  }

  /** Fase do disjuntor publicada pelo governo de capacidade, no formato {@code chave:FASE}. */
  private VerificationResult circuitPhase(
      ExpectedObservation observation, Map<String, String> facts) {
    return closedEnumFact(
        observation,
        facts,
        expected -> {
          try {
            CircuitPhase.valueOf(expected);
            return true;
          } catch (IllegalArgumentException unknown) {
            return false;
          }
        },
        "fase de disjuntor");
  }

  /**
   * Token de fencing preservado: o cenário declara apenas a chave do fato e a comparação é contra
   * {@value #FENCING_UNCHANGED}. Qualquer outro valor é recusa explícita, nunca omissão.
   */
  private VerificationResult fencingTokenUnchanged(
      ExpectedObservation observation, Map<String, String> facts) {
    String key = observation.expectedValue() == null ? "" : observation.expectedValue().trim();
    if (key.isEmpty()) {
      return notObserved(observation, "Observação de fencing sem chave de fato declarada.");
    }
    String observed = facts.get(key);
    if (observed == null) {
      return notObserved(observation, "O governo de capacidade não publicou o fato de fencing.");
    }
    if (FENCING_UNCHANGED.equals(observed)) {
      return result(
          observation,
          VerificationStatus.PASSED,
          observed,
          Map.of("reasonCode", FailureLabRedaction.safeReason(observed)),
          "A recusa aconteceu antes da posse: a marca de posse do agendamento ficou intacta.");
    }
    return result(
        observation,
        VerificationStatus.FAILED,
        observed,
        Map.of("reasonCode", FailureLabRedaction.safeReason(observed)),
        "A marca de posse do agendamento mudou apesar da recusa de admissão.");
  }

  private VerificationResult closedEnumFact(
      ExpectedObservation observation,
      Map<String, String> facts,
      java.util.function.Predicate<String> knownValue,
      String subject) {
    String raw = observation.expectedValue() == null ? "" : observation.expectedValue().trim();
    int separator = raw.indexOf(':');
    if (separator <= 0) {
      return notObserved(observation, "Observação de capacidade sem chave de fato declarada.");
    }
    String key = raw.substring(0, separator);
    String expected = raw.substring(separator + 1).toUpperCase(Locale.ROOT);
    if (!knownValue.test(expected)) {
      return result(
          observation,
          VerificationStatus.INCONCLUSIVE,
          "",
          Map.of("reasonCode", "UNKNOWN_EXPECTED_VALUE"),
          "O cenário declara " + subject + " fora do conjunto fechado conhecido.");
    }
    String observed = facts.get(key);
    if (observed == null) {
      return notObserved(observation, "O governo de capacidade não publicou o fato esperado.");
    }
    if (observed.equals(expected)) {
      return result(
          observation,
          VerificationStatus.PASSED,
          observed,
          Map.of("reasonCode", FailureLabRedaction.safeReason(observed)),
          "O governo de capacidade confirmou o " + subject + " esperado.");
    }
    return result(
        observation,
        VerificationStatus.INCONCLUSIVE,
        observed,
        Map.of("reasonCode", FailureLabRedaction.safeReason(observed)),
        "O governo de capacidade respondeu com " + subject + " diferente do declarado.");
  }

  private VerificationResult noSecretExposed(
      FailureLabRun run, ExpectedObservation observation, List<VerificationResult> accumulated) {
    List<String> inspected = new ArrayList<>();
    run.parameters()
        .forEach(
            (key, value) -> {
              inspected.add(key);
              inspected.add(value);
            });
    inspected.add(run.requestedBy());
    inspected.add(run.failureMessage());
    inspected.add(run.evidenceSummary());
    inspected.addAll(run.executionRefs());
    List<VerificationResult> previousResults =
        accumulated.isEmpty() ? run.verificationResults() : accumulated;
    for (VerificationResult previous : previousResults) {
      inspected.add(previous.observed());
      inspected.add(previous.explanation());
      previous.safeReferences().forEach((key, value) -> inspected.add(key + "=" + value));
    }
    for (String candidate : inspected) {
      if (FailureLabRedaction.looksSensitive(candidate)) {
        return result(
            observation,
            VerificationStatus.FAILED,
            "SENSITIVE_MARKER_PRESENT",
            Map.of(),
            "Um marcador sensível foi detectado no conteúdo da execução controlada.");
      }
    }
    return result(
        observation,
        VerificationStatus.PASSED,
        "true",
        Map.of("inspectedFields", String.valueOf(inspected.size())),
        "Nenhum indício de credencial ou dado protegido na evidência.");
  }

  private List<ExecutionControlRecord> controls(FailureLabRun run, ExecutionControlStorePort store) {
    List<ExecutionControlRecord> records = new ArrayList<>();
    for (String executionId : run.executionRefs()) {
      store.findByExecutionId(executionId).ifPresent(records::add);
    }
    return records;
  }

  private List<ExecutionWaitRecord> waits(FailureLabRun run, ExecutionWaitStorePort store) {
    List<ExecutionWaitRecord> waits = new ArrayList<>();
    for (String executionId : run.executionRefs()) {
      waits.addAll(store.findByExecutionId(executionId));
    }
    return waits;
  }

  private VerificationResult healthUnavailable(
      ExpectedObservation observation, HealthLookup health) {
    if (!health.available()) {
      return notApplicable(observation, "operationalHealthQueryService");
    }
    return result(
        observation,
        VerificationStatus.INCONCLUSIVE,
        "",
        Map.of("reasonCode", FailureLabRedaction.safeReason(health.failureReason())),
        "A leitura operacional não pôde ser obtida nesta configuração.");
  }

  private VerificationResult inconclusiveHealth(ExpectedObservation observation, String observed) {
    return result(
        observation,
        VerificationStatus.INCONCLUSIVE,
        observed,
        Map.of("healthWindow", HEALTH_WINDOW),
        "A leitura operacional não confirma nem contradiz a observação com a amostra atual.");
  }

  private VerificationResult notApplicable(ExpectedObservation observation, String missingSource) {
    return result(
        observation,
        VerificationStatus.NOT_APPLICABLE,
        "",
        Map.of("missingSource", missingSource),
        "Fonte canônica necessária indisponível nesta configuração.");
  }

  private VerificationResult notObserved(ExpectedObservation observation, String explanation) {
    return result(observation, VerificationStatus.NOT_OBSERVED, "", Map.of(), explanation);
  }

  private VerificationResult result(
      ExpectedObservation observation,
      VerificationStatus status,
      String observed,
      Map<String, String> safeReferences,
      String explanation) {
    Map<String, String> references = new LinkedHashMap<>(safeReferences);
    references.put("sourceType", observation.sourceType());
    return new VerificationResult(
        observation.code(),
        status,
        clock.now(),
        observation.expectedValue(),
        observed,
        FailureLabRedaction.sanitize(references),
        explanation);
  }

  private static String[] splitExpected(String expectedValue) {
    String value = expectedValue == null ? "" : expectedValue.trim().toUpperCase(Locale.ROOT);
    int separator = value.indexOf(':');
    if (separator < 0) {
      return new String[] {null, value};
    }
    return new String[] {value.substring(0, separator), value.substring(separator + 1)};
  }

  private static int parseInt(String value, int fallback) {
    try {
      return Integer.parseInt(value.trim());
    } catch (RuntimeException invalid) {
      return fallback;
    }
  }

  /** Consulta preguiçosa da saúde operacional — no máximo uma leitura por verificação. */
  private static final class HealthLookup {
    private final ObjectProvider<OperationalHealthQueryService> provider;
    private boolean resolved;
    private OperationalHealthSnapshot snapshot;
    private String failureReason = "UNAVAILABLE";

    private HealthLookup(ObjectProvider<OperationalHealthQueryService> provider) {
      this.provider = provider;
    }

    boolean available() {
      return provider.getIfAvailable() != null;
    }

    String failureReason() {
      return failureReason;
    }

    OperationalHealthSnapshot snapshot() {
      if (resolved) {
        return snapshot;
      }
      resolved = true;
      OperationalHealthQueryService service = provider.getIfAvailable();
      if (service == null) {
        return null;
      }
      try {
        snapshot = service.getSnapshot(HEALTH_WINDOW);
      } catch (RuntimeException failure) {
        failureReason = failure.getClass().getSimpleName();
        snapshot = null;
      }
      return snapshot;
    }
  }
}
