package br.com.banco.spider.operational.capacity;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.Duration;
import org.junit.jupiter.api.Test;

/**
 * Transições do disjuntor observadas com relógio controlado: a passagem de aberto para prova nunca
 * depende de tempo de parede nem de thread de fundo.
 */
class CircuitBreakerServiceTest {

  private static final Duration OPEN_FOR = Duration.ofSeconds(30);

  private final CapacityTestSupport.MutableClock clock =
      new CapacityTestSupport.MutableClock(CapacityTestSupport.T0);
  private final CircuitBreakerService circuits =
      new CircuitBreakerService(clock, CapacityTestSupport.silentTelemetry());

  @Test
  void policyWithoutThresholdNeverOpens() {
    CapacityPolicy policy = policy(0, OPEN_FOR);

    for (int attempt = 0; attempt < 10; attempt++) {
      circuits.recordFailure(policy.scopeKey(), policy);
    }

    assertEquals(CircuitPhase.CLOSED, circuits.phase(policy.scopeKey()));
    assertTrue(circuits.allowRequest(policy.scopeKey(), policy));
  }

  @Test
  void thresholdInsideTheWindowOpensTheCircuit() {
    CapacityPolicy policy = policy(3, OPEN_FOR);

    circuits.recordFailure(policy.scopeKey(), policy);
    circuits.recordFailure(policy.scopeKey(), policy);
    assertEquals(CircuitPhase.CLOSED, circuits.phase(policy.scopeKey()));

    circuits.recordFailure(policy.scopeKey(), policy);

    assertEquals(CircuitPhase.OPEN, circuits.phase(policy.scopeKey()));
    assertFalse(circuits.allowRequest(policy.scopeKey(), policy));
  }

  @Test
  void failuresOlderThanTheWindowDoNotAccumulate() {
    CapacityPolicy policy = policy(3, OPEN_FOR);

    circuits.recordFailure(policy.scopeKey(), policy);
    circuits.recordFailure(policy.scopeKey(), policy);
    clock.advance(CapacityTestSupport.WINDOW.plusSeconds(1));
    circuits.recordFailure(policy.scopeKey(), policy);

    assertEquals(CircuitPhase.CLOSED, circuits.phase(policy.scopeKey()));
  }

  @Test
  void successClearsTheAccumulatedFailuresWhileClosed() {
    CapacityPolicy policy = policy(2, OPEN_FOR);

    circuits.recordFailure(policy.scopeKey(), policy);
    circuits.recordSuccess(policy.scopeKey(), policy);
    circuits.recordFailure(policy.scopeKey(), policy);

    assertEquals(CircuitPhase.CLOSED, circuits.phase(policy.scopeKey()));
  }

  @Test
  void openCircuitBecomesHalfOpenOnlyAfterTheDeclaredDuration() {
    CapacityPolicy policy = policy(2, OPEN_FOR);
    open(policy);

    clock.advance(OPEN_FOR.minusSeconds(1));
    assertFalse(circuits.allowRequest(policy.scopeKey(), policy));
    assertEquals(CircuitPhase.OPEN, circuits.phase(policy.scopeKey()));

    clock.advance(Duration.ofSeconds(1));
    assertTrue(circuits.allowRequest(policy.scopeKey(), policy), "a prova deve ser liberada");
    assertEquals(CircuitPhase.HALF_OPEN, circuits.phase(policy.scopeKey()));
  }

  @Test
  void halfOpenAllowsOnlyTheDeclaredProbeCount() {
    CapacityPolicy policy = policy(2, OPEN_FOR);
    open(policy);
    clock.advance(OPEN_FOR);

    assertTrue(circuits.allowRequest(policy.scopeKey(), policy));
    assertFalse(circuits.allowRequest(policy.scopeKey(), policy), "uma prova por vez");
  }

  @Test
  void successfulProbeClosesTheCircuitAgain() {
    CapacityPolicy policy = policy(2, OPEN_FOR);
    open(policy);
    clock.advance(OPEN_FOR);
    assertTrue(circuits.allowRequest(policy.scopeKey(), policy));

    circuits.recordSuccess(policy.scopeKey(), policy);

    assertEquals(CircuitPhase.CLOSED, circuits.phase(policy.scopeKey()));
    assertTrue(circuits.allowRequest(policy.scopeKey(), policy));
  }

  @Test
  void failedProbeReopensTheCircuitForAnotherFullDuration() {
    CapacityPolicy policy = policy(2, OPEN_FOR);
    open(policy);
    clock.advance(OPEN_FOR);
    assertTrue(circuits.allowRequest(policy.scopeKey(), policy));

    circuits.recordFailure(policy.scopeKey(), policy);

    assertEquals(CircuitPhase.OPEN, circuits.phase(policy.scopeKey()));
    clock.advance(OPEN_FOR.minusSeconds(1));
    assertFalse(circuits.allowRequest(policy.scopeKey(), policy));
  }

  @Test
  void statesExposeThePhaseAndTheProbeDeadlinePerScope() {
    CapacityPolicy policy = policy(2, OPEN_FOR);
    open(policy);

    CircuitState state =
        circuits.states().stream()
            .filter(candidate -> candidate.scopeKey().equals(policy.scopeKey()))
            .findFirst()
            .orElseThrow();

    assertEquals(CircuitPhase.OPEN, state.phase());
    assertEquals(CapacityTestSupport.T0, state.openedAt());
    assertEquals(CapacityTestSupport.T0.plus(OPEN_FOR), state.probeAfter());
  }

  @Test
  void scopesAreIsolatedFromEachOther() {
    CapacityPolicy first = policy(2, OPEN_FOR);
    CapacityPolicy second =
        CapacityTestSupport.policy(
            "circuit-second",
            CapacityTestSupport.limits(0, -1, -1, 0),
            CapacityPolicyState.ACTIVE,
            2,
            OPEN_FOR);
    open(first);

    assertEquals(CircuitPhase.OPEN, circuits.phase(first.scopeKey()));
    assertEquals(CircuitPhase.CLOSED, circuits.phase(second.scopeKey()));
    assertTrue(circuits.allowRequest(second.scopeKey(), second));
  }

  private void open(CapacityPolicy policy) {
    for (int attempt = 0; attempt < policy.circuitFailureThreshold(); attempt++) {
      circuits.recordFailure(policy.scopeKey(), policy);
    }
    assertEquals(CircuitPhase.OPEN, circuits.phase(policy.scopeKey()));
  }

  private static CapacityPolicy policy(int threshold, Duration openDuration) {
    return CapacityTestSupport.policy(
        "circuit",
        CapacityTestSupport.limits(0, -1, -1, 0),
        CapacityPolicyState.ACTIVE,
        threshold,
        openDuration);
  }
}
