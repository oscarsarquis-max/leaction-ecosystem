package br.com.banco.spider.operational.failurelab;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.domain.TechnicalStatus;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.persistence.port.StepAttemptStorePort;
import br.com.banco.spider.execution.step.AttemptState;
import br.com.banco.spider.execution.step.StepAttemptRecord;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionControlStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryExecutionWaitStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryOperationalEventStore;
import br.com.banco.spider.infrastructure.persistence.memory.InMemoryStepAttemptStore;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import br.com.banco.spider.operational.health.OperationalHealthQueryService;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.NoSuchBeanDefinitionException;
import org.springframework.beans.factory.ObjectProvider;

class FailureLabObservationVerifierTest {

  private static final Instant NOW = Instant.parse("2026-01-01T10:00:00Z");
  private static final String EXECUTION_ID = "exec-lab-1";
  private static final String ENTRY_STEP = "step-1";

  private final SpiderClock clock = SpiderClock.fixed(NOW);
  private final ExecutionControlStorePort controls = new InMemoryExecutionControlStore();
  private final StepAttemptStorePort attempts = new InMemoryStepAttemptStore();
  private final ExecutionWaitStorePort waits = new InMemoryExecutionWaitStore();
  private final OperationalEventStorePort events = new InMemoryOperationalEventStore();

  private FailureLabObservationVerifier verifier;

  @BeforeEach
  void buildVerifier() {
    verifier =
        new FailureLabObservationVerifier(
            clock,
            providerOf(controls),
            providerOf(attempts),
            providerOf(waits),
            providerOf(events),
            providerOf((CallbackOutboxStorePort) null),
            providerOf((OperationalHealthQueryService) null));
  }

  @Test
  void executionStateIsPassedWhenControlRecordMatches() {
    controls.insert(control(ExecutionState.SUCCEEDED));

    VerificationResult result =
        single(
            observation(
                "EXECUTION_SUCCEEDED",
                "EXECUTION_CONTROL",
                ObservationPredicateType.EXECUTION_REACHED_STATE,
                "SUCCEEDED"));

    assertEquals(VerificationStatus.PASSED, result.status());
    assertEquals("SUCCEEDED", result.observed());
    assertEquals(NOW, result.observedAt());
  }

  @Test
  void executionStateIsFailedWhenControlRecordDiverges() {
    controls.insert(control(ExecutionState.FAILED));

    VerificationResult result =
        single(
            observation(
                "EXECUTION_SUCCEEDED",
                "EXECUTION_CONTROL",
                ObservationPredicateType.EXECUTION_REACHED_STATE,
                "SUCCEEDED"));

    assertEquals(VerificationStatus.FAILED, result.status());
    assertEquals("FAILED", result.observed());
  }

  @Test
  void attemptCountIsPassedWithTwoRecordedAttempts() {
    attempts.insert(attempt("attempt-1", 1, AttemptState.FAILED));
    attempts.insert(attempt("attempt-2", 2, AttemptState.SUCCEEDED));

    VerificationResult result =
        single(
            observation(
                "AT_LEAST_TWO_ATTEMPTS",
                "STEP_ATTEMPT",
                ObservationPredicateType.ATTEMPT_COUNT_AT_LEAST,
                "2"));

    assertEquals(VerificationStatus.PASSED, result.status());
    assertEquals("2", result.observed());
    assertEquals(ENTRY_STEP, result.safeReferences().get("stepRef"));
  }

  @Test
  void attemptCountIsFailedWhenBelowTheDeclaredMinimum() {
    attempts.insert(attempt("attempt-1", 1, AttemptState.SUCCEEDED));

    VerificationResult result =
        single(
            observation(
                "AT_LEAST_TWO_ATTEMPTS",
                "STEP_ATTEMPT",
                ObservationPredicateType.ATTEMPT_COUNT_AT_LEAST,
                "2"));

    assertEquals(VerificationStatus.FAILED, result.status());
  }

  @Test
  void missingEvidenceForRequiredObservationIsNotObservedInsteadOfPassed() {
    VerificationResult event =
        single(
            observation(
                "TELEMETRY_EXECUTION_SUCCEEDED",
                "OPERATIONAL_EVENT",
                ObservationPredicateType.OPERATIONAL_EVENT_EMITTED,
                "EXECUTION_SUCCEEDED"));
    assertEquals(VerificationStatus.NOT_OBSERVED, event.status());

    VerificationResult wait =
        single(
            observation(
                "WAIT_OPENED", "EXECUTION_WAIT", ObservationPredicateType.WAIT_OPENED, "true"));
    assertEquals(VerificationStatus.NOT_OBSERVED, wait.status());

    VerificationResult attemptCount =
        single(
            observation(
                "AT_LEAST_TWO_ATTEMPTS",
                "STEP_ATTEMPT",
                ObservationPredicateType.ATTEMPT_COUNT_AT_LEAST,
                "2"));
    assertEquals(VerificationStatus.NOT_OBSERVED, attemptCount.status());
  }

  @Test
  void noSecretExposedIsPassedForACleanRun() {
    controls.insert(control(ExecutionState.SUCCEEDED));

    List<VerificationResult> results =
        verifier.verify(
            run(),
            scenario(
                observation(
                    "EXECUTION_SUCCEEDED",
                    "EXECUTION_CONTROL",
                    ObservationPredicateType.EXECUTION_REACHED_STATE,
                    "SUCCEEDED"),
                observation(
                    "NO_SECRET_EXPOSED",
                    "FAILURE_LAB_RUN",
                    ObservationPredicateType.NO_SECRET_EXPOSED,
                    "true")),
            Map.of());

    VerificationResult secrets = byCode(results, "NO_SECRET_EXPOSED");
    assertEquals(VerificationStatus.PASSED, secrets.status());
    assertEquals("true", secrets.observed());
  }

  @Test
  void noSecretExposedIsFailedWhenASensitiveMarkerLeaksIntoTheRun() {
    FailureLabRun leaking =
        run().completed(
                FailureLabRunStatus.OBSERVING,
                NOW,
                List.of(
                    new VerificationResult(
                        "SOME_OBSERVATION",
                        VerificationStatus.PASSED,
                        NOW,
                        "true",
                        "bearer abc",
                        Map.of(),
                        "")),
                null,
                null);

    List<VerificationResult> results =
        verifier.verify(
            leaking,
            scenario(
                observation(
                    "NO_SECRET_EXPOSED",
                    "FAILURE_LAB_RUN",
                    ObservationPredicateType.NO_SECRET_EXPOSED,
                    "true")),
            Map.of());

    assertEquals(VerificationStatus.FAILED, results.getFirst().status());
    assertEquals("SENSITIVE_MARKER_PRESENT", results.getFirst().observed());
  }

  @Test
  void healthPredicatesAreNotApplicableWhenTheReadingServiceIsAbsent() {
    List<VerificationResult> results =
        verifier.verify(
            run(),
            scenario(
                observation(
                    "HEALTH_OVERALL_INSUFFICIENT_DATA",
                    "OPERATIONAL_HEALTH",
                    ObservationPredicateType.HEALTH_OVERALL_STATUS,
                    "INSUFFICIENT_DATA"),
                observation(
                    "SLI_INSUFFICIENT_DATA",
                    "OPERATIONAL_HEALTH",
                    ObservationPredicateType.SLI_STATUS_EQUALS,
                    "INSUFFICIENT_DATA"),
                observation(
                    "EXECUTION_FLOW_DEGRADED",
                    "OPERATIONAL_HEALTH",
                    ObservationPredicateType.HEALTH_DIMENSION_REACHED_STATUS,
                    "EXECUTION_FLOW:UNHEALTHY")),
            Map.of());

    assertEquals(3, results.size());
    for (VerificationResult result : results) {
      assertEquals(VerificationStatus.NOT_APPLICABLE, result.status());
      assertEquals(
          "operationalHealthQueryService", result.safeReferences().get("missingSource"));
    }
  }

  @Test
  void unavailableCanonicalSourceIsNotApplicableRatherThanFailed() {
    FailureLabObservationVerifier withoutStores =
        new FailureLabObservationVerifier(
            clock,
            providerOf((ExecutionControlStorePort) null),
            providerOf((StepAttemptStorePort) null),
            providerOf((ExecutionWaitStorePort) null),
            providerOf((OperationalEventStorePort) null),
            providerOf((CallbackOutboxStorePort) null),
            providerOf((OperationalHealthQueryService) null));

    List<VerificationResult> results =
        withoutStores.verify(
            run(),
            scenario(
                observation(
                    "EXECUTION_SUCCEEDED",
                    "EXECUTION_CONTROL",
                    ObservationPredicateType.EXECUTION_REACHED_STATE,
                    "SUCCEEDED")),
            Map.of());

    assertEquals(VerificationStatus.NOT_APPLICABLE, results.getFirst().status());
    assertEquals("executionControlStore", results.getFirst().safeReferences().get("missingSource"));
  }

  @Test
  void runtimeFactsConfirmASecurityRejectionWithoutAnyEvent() {
    VerificationResult result =
        verifier
            .verify(
                run(),
                scenario(
                    observation(
                        "SIGNAL_REJECTED_SECURITY",
                        "SIGNAL_INGRESS",
                        ObservationPredicateType.SIGNAL_REJECTED_WITH_CATEGORY,
                        "SECURITY")),
                Map.of("signalOutcome", "UNAUTHORIZED", "signalCategory", "SECURITY"))
            .getFirst();

    assertEquals(VerificationStatus.PASSED, result.status());
    assertEquals("UNAUTHORIZED", result.observed());
  }

  @Test
  void everyResultCarriesTheDeclaredSourceType() {
    controls.insert(control(ExecutionState.SUCCEEDED));

    VerificationResult result =
        single(
            observation(
                "EXECUTION_SUCCEEDED",
                "EXECUTION_CONTROL",
                ObservationPredicateType.EXECUTION_REACHED_STATE,
                "SUCCEEDED"));

    assertTrue(result.safeReferences().containsKey("sourceType"));
    assertEquals("EXECUTION_CONTROL", result.safeReferences().get("sourceType"));
  }

  private VerificationResult single(ExpectedObservation observation) {
    return verifier.verify(run(), scenario(observation), Map.of()).getFirst();
  }

  private static VerificationResult byCode(List<VerificationResult> results, String code) {
    return results.stream()
        .filter(result -> result.observationCode().equals(code))
        .findFirst()
        .orElseThrow(() -> new AssertionError("observação ausente: " + code));
  }

  private static FailureLabRun run() {
    return FailureLabRun.requested(
            "labrun-1", scenario(), Map.of("note", "cenario controlado"), "operator-test", NOW)
        .withExecutionRefs(List.of(EXECUTION_ID));
  }

  private static FailureScenarioDefinition scenario(ExpectedObservation... observations) {
    List<ExpectedObservation> declared =
        observations.length == 0
            ? List.of(
                new ExpectedObservation(
                    "NO_SECRET_EXPOSED",
                    "",
                    "FAILURE_LAB_RUN",
                    ObservationPredicateType.NO_SECRET_EXPOSED,
                    "true",
                    true))
            : List.of(observations);
    return new FailureScenarioDefinition(
        1,
        "TEST_SCENARIO",
        "1.0",
        "Cenário de teste",
        "Cenário sintético para verificação de observações.",
        FailureScenarioCategory.EXECUTION,
        FailureScenarioDefinition.MOCK_ONLY,
        List.of(),
        List.of("note"),
        declared,
        Duration.ofMinutes(2),
        1,
        "runbook:failure-lab:retry@1.0",
        "SUCCESS",
        "TEST_SCENARIO");
  }

  private static ExpectedObservation observation(
      String code, String sourceType, ObservationPredicateType predicate, String expectedValue) {
    return new ExpectedObservation(code, "", sourceType, predicate, expectedValue, true);
  }

  private static ExecutionControlRecord control(ExecutionState state) {
    return new ExecutionControlRecord(
        EXECUTION_ID,
        "ctx:failure-lab",
        "corr-lab",
        "plan-lab",
        "failure-lab-test",
        "1.0.0",
        state,
        1,
        state == ExecutionState.SUCCEEDED ? TechnicalStatus.SUCCESS : TechnicalStatus.FAILURE,
        NOW.minusSeconds(1),
        NOW,
        NOW,
        null,
        "retention:test",
        null);
  }

  private static StepAttemptRecord attempt(String attemptId, int number, AttemptState state) {
    return new StepAttemptRecord(
        attemptId,
        EXECUTION_ID,
        ENTRY_STEP,
        number,
        "inv-" + number,
        "binding:mock@1.0.0",
        NOW.minusSeconds(2),
        NOW.plusSeconds(30),
        NOW,
        state,
        null,
        null,
        null,
        null,
        List.of());
  }

  /** ObjectProvider mínimo: {@code null} representa a ausência do bean no contexto. */
  private static <T> ObjectProvider<T> providerOf(T value) {
    return new ObjectProvider<>() {
      @Override
      public T getObject() {
        if (value == null) {
          throw new NoSuchBeanDefinitionException("bean ausente no contexto de teste");
        }
        return value;
      }

      @Override
      public T getObject(Object... args) {
        return getObject();
      }

      @Override
      public T getIfAvailable() {
        return value;
      }

      @Override
      public T getIfUnique() {
        return value;
      }
    };
  }
}
