package br.com.banco.spider.operational.capacity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import br.com.banco.spider.config.CapacityProperties;
import br.com.banco.spider.execution.support.IdentifierGenerator;
import br.com.banco.spider.operational.workers.WorkerBacklogQueryService;
import br.com.banco.spider.operational.workers.WorkerRuntimeCatalog;
import br.com.banco.spider.operational.workers.WorkerType;
import java.time.Duration;
import java.util.List;
import org.junit.jupiter.api.Test;

/**
 * Cada desfecho de admissão precisa ser alcançável e distinguível. Em observação o desfecho
 * pretendido é registrado sem nunca barrar trabalho.
 */
class CapacityAdmissionServiceTest {

  @Test
  void disabledModuleAdmitsWithoutConsultingAnyPolicy() {
    Fixture fixture = new Fixture(false, false);
    CapacityPolicy policy = CapacityTestSupport.policy("off", CapacityTestSupport.limits(1, -1, -1, 0));

    AdmissionDecision decision = fixture.admission.evaluate(CapacityTestSupport.request(policy));

    assertEquals(AdmissionResult.ADMITTED, decision.result());
    assertEquals(AdmissionDecision.MONITOR_BYPASS, decision.reasonCode());
    assertTrue(decision.monitorOnly());
    assertNull(decision.policyRef());
    assertEquals(CapacityMode.DISABLED, fixture.admission.mode());
    assertTrue(fixture.decisions.recent(0).isEmpty(), "módulo desligado não registra decisão");
  }

  @Test
  void requestWithoutSpecificScopeFallsBackToTheGlobalPolicy() {
    Fixture fixture = new Fixture(true, true);

    AdmissionDecision decision = fixture.admission.evaluate(unmatchedRequest());

    assertEquals(AdmissionResult.ADMITTED, decision.result());
    assertEquals(CapacityScopeType.GLOBAL, decision.scopeType());
    assertEquals("capacity:global@1.0", decision.policyRef());
    assertEquals(1, fixture.decisions.recent(0).size());
  }

  @Test
  void requestWithoutAnyMatchingPolicyIsAdmittedAndRecorded() {
    CapacityPolicy scoped =
        CapacityTestSupport.policy("scoped-only", CapacityTestSupport.limits(1, -1, -1, 0));
    Fixture fixture = new Fixture(true, true, true, 10, new CapacityPolicyCatalog(List.of(scoped)));

    AdmissionDecision decision = fixture.admission.evaluate(unmatchedRequest());

    assertEquals(AdmissionResult.ADMITTED, decision.result());
    assertEquals(AdmissionDecision.NO_POLICY_MATCH, decision.reasonCode());
    assertNull(decision.policyRef());
    assertEquals(1, fixture.decisions.recent(0).size());
  }

  private static AdmissionRequest unmatchedRequest() {
    return new AdmissionRequest(
        "test:unmatched",
        CapacityScopeType.SCHEDULE,
        "sched:not-in-catalog@1",
        null,
        "sched:not-in-catalog@1",
        null,
        null,
        CapacityTestSupport.T0,
        "corr-test");
  }

  @Test
  void saturatedConcurrencyIsRejectedByCapacity() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy("bulkhead", CapacityTestSupport.limits(1, -1, -1, 0));
    fixture.bulkheads.register(policy.scopeKey(), 1);
    assertTrue(fixture.bulkheads.tryAcquire(policy.scopeKey(), 1));

    AdmissionDecision decision =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    assertEquals(AdmissionResult.REJECTED_CAPACITY, decision.result());
    assertEquals(ShedReason.CONCURRENCY_EXHAUSTED, decision.shedReason());
    assertFalse(decision.monitorOnly());
    assertFalse(decision.allowsWork());
  }

  @Test
  void exhaustedQuotaIsRejectedByQuota() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy("quota", CapacityTestSupport.limits(0, -1, -1, 1));

    assertEquals(
        AdmissionResult.ADMITTED,
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy).result());
    AdmissionDecision rejected =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    assertEquals(AdmissionResult.REJECTED_QUOTA, rejected.result());
    assertEquals(ShedReason.QUOTA_EXHAUSTED, rejected.shedReason());
  }

  @Test
  void openCircuitIsRejectedBeforeAnythingElseIsConsumed() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy(
            "circuit",
            CapacityTestSupport.limits(0, -1, -1, 1),
            CapacityPolicyState.ACTIVE,
            2,
            Duration.ofMinutes(5));
    fixture.circuits.recordFailure(policy.scopeKey(), policy);
    fixture.circuits.recordFailure(policy.scopeKey(), policy);

    AdmissionDecision decision =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    assertEquals(AdmissionResult.REJECTED_CIRCUIT_OPEN, decision.result());
    assertEquals(ShedReason.CIRCUIT_OPEN, decision.shedReason());
    assertEquals(
        0,
        fixture.quotas.used(policy.scopeKey(), policy.limits().window()),
        "recusa pelo disjuntor não deve consumir quota");
  }

  @Test
  void hardBacklogLimitShedsTheRequest() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy("backlog", CapacityTestSupport.limits(0, 0, 0, 0));

    AdmissionDecision decision =
        fixture.admission.evaluate(
            CapacityTestSupport.request(policy, WorkerType.CALLBACK_DELIVERY.name()), policy);

    assertEquals(AdmissionResult.SHED, decision.result());
    assertEquals(ShedReason.BACKLOG_HARD_LIMIT, decision.shedReason());
  }

  @Test
  void softBacklogLimitOnlyDelaysTheRequest() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy("soft-backlog", CapacityTestSupport.limits(0, 0, 5, 0));

    AdmissionDecision decision =
        fixture.admission.evaluate(
            CapacityTestSupport.request(policy, WorkerType.CALLBACK_DELIVERY.name()), policy);

    assertEquals(AdmissionResult.DELAYED, decision.result());
    assertNull(decision.shedReason());
  }

  @Test
  void unknownBacklogNeverShedsOnAbsentEvidence() {
    Fixture fixture = new Fixture(true, true, false);
    CapacityPolicy policy =
        CapacityTestSupport.policy("backlog-unknown", CapacityTestSupport.limits(0, 0, 0, 0));

    AdmissionDecision decision =
        fixture.admission.evaluate(
            CapacityTestSupport.request(policy, WorkerType.CALLBACK_DELIVERY.name()), policy);

    assertEquals(AdmissionResult.ADMITTED, decision.result());
  }

  @Test
  void monitorOnlyModeAdmitsButRecordsTheIntendedRejection() {
    Fixture fixture = new Fixture(true, false);
    CapacityPolicy policy =
        CapacityTestSupport.policy("monitor", CapacityTestSupport.limits(1, -1, -1, 0));
    fixture.bulkheads.register(policy.scopeKey(), 1);
    assertTrue(fixture.bulkheads.tryAcquire(policy.scopeKey(), 1));

    AdmissionDecision decision =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    assertEquals(AdmissionResult.ADMITTED, decision.result());
    assertTrue(decision.monitorOnly());
    assertTrue(decision.allowsWork());
    assertEquals(
        AdmissionDecision.MONITOR_ONLY_PREFIX + AdmissionResult.REJECTED_CAPACITY.name(),
        decision.reasonCode());
    assertEquals(CapacityMode.MONITOR_ONLY, fixture.admission.mode());
  }

  @Test
  void monitorOnlyPolicyIsNotEnforcedEvenWhenTheModuleEnforces() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy(
            "policy-monitor",
            CapacityTestSupport.limits(1, -1, -1, 0),
            CapacityPolicyState.MONITOR_ONLY,
            0,
            Duration.ZERO);
    fixture.bulkheads.register(policy.scopeKey(), 1);
    assertTrue(fixture.bulkheads.tryAcquire(policy.scopeKey(), 1));

    AdmissionDecision decision =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    assertEquals(AdmissionResult.ADMITTED, decision.result());
    assertTrue(decision.monitorOnly());
  }

  @Test
  void disabledPolicyAdmitsWithoutEvaluatingLimits() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy(
            "policy-off",
            CapacityTestSupport.limits(1, -1, -1, 0),
            CapacityPolicyState.DISABLED,
            0,
            Duration.ZERO);

    AdmissionDecision decision =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    assertEquals(AdmissionResult.ADMITTED, decision.result());
    assertEquals(AdmissionDecision.POLICY_DISABLED, decision.reasonCode());
  }

  @Test
  void shedIsRecordedWhenTheReservationDisappearsAfterAdmission() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy("late-shed", CapacityTestSupport.limits(1, -1, -1, 0));
    AdmissionDecision admitted =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);
    assertEquals(AdmissionResult.ADMITTED, admitted.result());

    AdmissionDecision shed =
        fixture.admission.recordShed(admitted, ShedReason.CONCURRENCY_EXHAUSTED);

    assertEquals(AdmissionResult.SHED, shed.result());
    assertEquals(admitted.policyRef(), shed.policyRef());
    assertFalse(shed.monitorOnly());
    assertEquals(shed, fixture.decisions.recent(1).getFirst());
  }

  @Test
  void technicalFailuresFeedTheCircuitAndSuccessClearsIt() {
    Fixture fixture = new Fixture(true, true);
    CapacityPolicy policy =
        CapacityTestSupport.policy(
            "outcome",
            CapacityTestSupport.limits(0, -1, -1, 0),
            CapacityPolicyState.ACTIVE,
            2,
            Duration.ofMinutes(5));
    AdmissionDecision decision =
        fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);

    fixture.admission.recordOutcome(decision, policy, true);
    assertEquals(CircuitPhase.CLOSED, fixture.circuits.phase(policy.scopeKey()));
    fixture.admission.recordOutcome(decision, policy, true);
    assertEquals(CircuitPhase.OPEN, fixture.circuits.phase(policy.scopeKey()));
  }

  @Test
  void decisionLogKeepsOnlyTheMostRecentEntries() {
    Fixture fixture = new Fixture(true, true, true, 3);
    CapacityPolicy policy =
        CapacityTestSupport.policy("ring", CapacityTestSupport.limits(0, -1, -1, 0));
    for (int attempt = 0; attempt < 5; attempt++) {
      fixture.admission.evaluate(CapacityTestSupport.request(policy), policy);
    }

    List<AdmissionDecision> recent = fixture.decisions.recent(0);

    assertEquals(3, recent.size());
    assertTrue(fixture.decisions.truncated());
    assertEquals(5, fixture.decisions.recordedTotal());
  }

  /** Montagem local do módulo — nenhum bean de aplicação é necessário. */
  private static final class Fixture {
    private final CapacityTestSupport.MutableClock clock =
        new CapacityTestSupport.MutableClock(CapacityTestSupport.T0);
    private final BulkheadService bulkheads = new BulkheadService(clock);
    private final CircuitBreakerService circuits =
        new CircuitBreakerService(clock, CapacityTestSupport.silentTelemetry());
    private final QuotaService quotas = new QuotaService(clock);
    private final CapacityDecisionStore decisions;
    private final CapacityAdmissionService admission;

    private Fixture(boolean enabled, boolean enforcing) {
      this(enabled, enforcing, true, CapacityDecisionStore.MAX_SIZE);
    }

    private Fixture(boolean enabled, boolean enforcing, boolean backlogAvailable) {
      this(enabled, enforcing, backlogAvailable, CapacityDecisionStore.MAX_SIZE);
    }

    private Fixture(
        boolean enabled, boolean enforcing, boolean backlogAvailable, int decisionLogSize) {
      this(
          enabled,
          enforcing,
          backlogAvailable,
          decisionLogSize,
          new CapacityPolicyCatalog(
              new com.fasterxml.jackson.databind.ObjectMapper().findAndRegisterModules()));
    }

    private Fixture(
        boolean enabled,
        boolean enforcing,
        boolean backlogAvailable,
        int decisionLogSize,
        CapacityPolicyCatalog catalog) {
      CapacityProperties properties = CapacityTestSupport.properties(enabled, enforcing);
      this.decisions = new CapacityDecisionStore(decisionLogSize);
      this.admission =
          new CapacityAdmissionService(
              properties,
              catalog,
              bulkheads,
              circuits,
              quotas,
              decisions,
              CapacityTestSupport.silentTelemetry(),
              clock,
              IdentifierGenerator.sequential("capacity-test"),
              CapacityTestSupport.provider(backlogAvailable ? emptyBacklog() : null));
    }

    /** Fontes canônicas vazias: fila pendente igual a zero, e observada de fato. */
    private WorkerBacklogQueryService emptyBacklog() {
      return new WorkerBacklogQueryService(
          new WorkerRuntimeCatalog(10, Duration.ofSeconds(30), Duration.ofSeconds(20), 3),
          clock,
          CapacityTestSupport.provider(null),
          CapacityTestSupport.provider(null),
          CapacityTestSupport.provider(
              new br.com.banco.spider.infrastructure.persistence.memory
                  .InMemoryCallbackOutboxStore()),
          CapacityTestSupport.provider(null),
          CapacityTestSupport.provider(null));
    }
  }
}
