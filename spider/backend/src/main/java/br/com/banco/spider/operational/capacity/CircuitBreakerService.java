package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.execution.support.SpiderClock;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.Deque;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Disjuntores em memória, um por escopo. Só o tempo do {@link SpiderClock} move as fases: a
 * passagem de OPEN para HALF_OPEN nunca depende de uma thread de fundo, o que mantém o
 * comportamento verificável com relógio controlado.
 */
public class CircuitBreakerService {

  private final SpiderClock clock;
  private final CapacityTelemetry telemetry;
  private final Map<String, Circuit> circuits = new ConcurrentHashMap<>();

  public CircuitBreakerService(SpiderClock clock, CapacityTelemetry telemetry) {
    this.clock = clock;
    this.telemetry = telemetry;
  }

  public boolean allowRequest(String scopeKey, CapacityPolicy policy) {
    if (scopeKey == null || policy == null || !policy.limitsCircuit()) {
      return true;
    }
    return circuit(scopeKey).allow(policy, clock.now());
  }

  public void recordSuccess(String scopeKey, CapacityPolicy policy) {
    if (scopeKey == null || policy == null || !policy.limitsCircuit()) {
      return;
    }
    circuit(scopeKey).success(policy, clock.now());
  }

  public void recordFailure(String scopeKey, CapacityPolicy policy) {
    if (scopeKey == null || policy == null || !policy.limitsCircuit()) {
      return;
    }
    circuit(scopeKey).failure(policy, clock.now());
  }

  public CircuitPhase phase(String scopeKey) {
    Circuit circuit = scopeKey == null ? null : circuits.get(scopeKey);
    return circuit == null ? CircuitPhase.CLOSED : circuit.phase();
  }

  public List<CircuitState> states() {
    Instant now = clock.now();
    List<CircuitState> states = new ArrayList<>();
    circuits.forEach((scopeKey, circuit) -> states.add(circuit.snapshot(scopeKey, now)));
    states.sort(Comparator.comparing(CircuitState::scopeKey));
    return List.copyOf(states);
  }

  private Circuit circuit(String scopeKey) {
    return circuits.computeIfAbsent(scopeKey, key -> new Circuit(key, telemetry));
  }

  /** Estado mutável de um disjuntor. Toda transição é serializada por instância. */
  private static final class Circuit {

    private final String scopeKey;
    private final CapacityTelemetry telemetry;
    private final Deque<Instant> failures = new ArrayDeque<>();

    private CircuitPhase phase = CircuitPhase.CLOSED;
    private int successCount;
    private int probeInFlight;
    private Instant openedAt;
    private Instant probeAfter;

    private Circuit(String scopeKey, CapacityTelemetry telemetry) {
      this.scopeKey = scopeKey;
      this.telemetry = telemetry;
    }

    synchronized CircuitPhase phase() {
      return phase;
    }

    synchronized boolean allow(CapacityPolicy policy, Instant now) {
      maybeHalfOpen(policy, now);
      return switch (phase) {
        case CLOSED -> true;
        case OPEN -> false;
        case HALF_OPEN -> {
          if (probeInFlight >= policy.effectiveProbeLimit()) {
            yield false;
          }
          probeInFlight++;
          yield true;
        }
      };
    }

    synchronized void success(CapacityPolicy policy, Instant now) {
      maybeHalfOpen(policy, now);
      if (phase == CircuitPhase.HALF_OPEN) {
        probeInFlight = Math.max(0, probeInFlight - 1);
        successCount++;
        if (successCount >= policy.effectiveProbeLimit()) {
          close(now);
        }
        return;
      }
      failures.clear();
    }

    synchronized void failure(CapacityPolicy policy, Instant now) {
      maybeHalfOpen(policy, now);
      if (phase == CircuitPhase.HALF_OPEN) {
        probeInFlight = Math.max(0, probeInFlight - 1);
        open(policy, now, "HALF_OPEN_PROBE_FAILED");
        return;
      }
      if (phase == CircuitPhase.OPEN) {
        return;
      }
      failures.addLast(now);
      pruneFailures(policy.circuitWindow(), now);
      if (failures.size() >= policy.circuitFailureThreshold()) {
        open(policy, now, "FAILURE_THRESHOLD_REACHED");
      }
    }

    synchronized CircuitState snapshot(String key, Instant now) {
      return new CircuitState(
          key, phase, failures.size(), successCount, openedAt, probeAfter, probeInFlight, now);
    }

    private void maybeHalfOpen(CapacityPolicy policy, Instant now) {
      if (phase != CircuitPhase.OPEN || probeAfter == null || probeAfter.isAfter(now)) {
        return;
      }
      phase = CircuitPhase.HALF_OPEN;
      successCount = 0;
      probeInFlight = 0;
      telemetry.emitCircuitTransition(scopeKey, CircuitPhase.HALF_OPEN, "OPEN_DURATION_ELAPSED");
    }

    private void open(CapacityPolicy policy, Instant now, String reasonCode) {
      phase = CircuitPhase.OPEN;
      openedAt = now;
      Duration openDuration = policy.circuitOpenDuration();
      probeAfter = now.plus(openDuration);
      successCount = 0;
      probeInFlight = 0;
      failures.clear();
      telemetry.emitCircuitTransition(scopeKey, CircuitPhase.OPEN, reasonCode);
    }

    private void close(Instant now) {
      phase = CircuitPhase.CLOSED;
      openedAt = null;
      probeAfter = null;
      successCount = 0;
      probeInFlight = 0;
      failures.clear();
      telemetry.emitCircuitTransition(scopeKey, CircuitPhase.CLOSED, "PROBES_SUCCEEDED");
    }

    private void pruneFailures(Duration window, Instant now) {
      Instant floor = now.minus(window);
      while (!failures.isEmpty() && failures.peekFirst().isBefore(floor)) {
        failures.removeFirst();
      }
    }
  }
}
