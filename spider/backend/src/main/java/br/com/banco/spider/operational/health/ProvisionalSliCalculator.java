package br.com.banco.spider.operational.health;

import br.com.banco.spider.execution.callback.CallbackOutboxState;
import br.com.banco.spider.execution.domain.ExecutionState;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumSet;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

public class ProvisionalSliCalculator {

  public static final String EXECUTION_TECHNICAL_RELIABILITY = "EXECUTION_TECHNICAL_RELIABILITY";
  public static final String EXECUTION_LATENCY_P95_MS = "EXECUTION_LATENCY_P95_MS";
  public static final String ASYNC_WAIT_AGED = "ASYNC_WAIT_AGED";
  public static final String CALLBACK_CONFIRMATION_RATIO = "CALLBACK_CONFIRMATION_RATIO";
  public static final String SIGNAL_ACCEPTANCE_RATIO = "SIGNAL_ACCEPTANCE_RATIO";
  public static final String TELEMETRY_COVERAGE = "TELEMETRY_COVERAGE";

  private static final Set<ExecutionState> RELIABILITY_TERMINAL =
      EnumSet.of(
          ExecutionState.SUCCEEDED,
          ExecutionState.FAILED,
          ExecutionState.TIMED_OUT,
          ExecutionState.REJECTED);
  private final SpiderClock clock;

  public ProvisionalSliCalculator(SpiderClock clock) {
    this.clock = clock;
  }

  public List<SliResult> calculate(
      List<SliDefinition> definitions, OperationalHealthData data, Duration agedWaitThreshold) {
    Map<String, SliResult> calculated = new LinkedHashMap<>();
    calculated.put(EXECUTION_TECHNICAL_RELIABILITY, reliability(data));
    calculated.put(EXECUTION_LATENCY_P95_MS, latency(data));
    calculated.put(ASYNC_WAIT_AGED, agedWaits(data, agedWaitThreshold));
    calculated.put(CALLBACK_CONFIRMATION_RATIO, callbacks(data));
    calculated.put(SIGNAL_ACCEPTANCE_RATIO, signals(data));
    calculated.put(TELEMETRY_COVERAGE, telemetryCoverage(data));
    List<SliResult> results = new ArrayList<>();
    for (SliDefinition definition : definitions) {
      SliResult raw = calculated.get(definition.code());
      if (raw == null) {
        results.add(insufficient(definition, 0, "Calculador não disponível"));
      } else if (raw.sampleSize() < definition.minimumSampleSize()) {
        results.add(
            new SliResult(
                1, raw.code(), raw.dimension(), SliStatus.INSUFFICIENT_DATA, null, raw.unit(),
                raw.sampleSize(), raw.statistics(), "Amostra abaixo do mínimo "
                    + definition.minimumSampleSize()));
      } else {
        results.add(raw);
      }
    }
    return List.copyOf(results);
  }

  private SliResult reliability(OperationalHealthData data) {
    Map<String, ExecutionState> states = new HashMap<>();
    data.executions().stream()
        .filter(e -> RELIABILITY_TERMINAL.contains(e.state()))
        .forEach(e -> states.put(e.executionId(), e.state()));
    for (OperationalEvent event : data.events()) {
      ExecutionState state = terminalState(event.eventType());
      if (state != null) {
        states.putIfAbsent(event.executionId(), state);
      }
    }
    long successes = states.values().stream().filter(s -> s == ExecutionState.SUCCEEDED).count();
    return ratio(
        EXECUTION_TECHNICAL_RELIABILITY, HealthDimensionCode.EXECUTION_FLOW, successes,
        states.size(), "Razão de execuções tecnicamente SUCCEEDED");
  }

  private SliResult latency(OperationalHealthData data) {
    Map<String, Long> durations = new HashMap<>();
    data.events().stream()
        .filter(
            e ->
                e.eventType() == OperationalEventType.EXECUTION_SUCCEEDED
                    || e.eventType() == OperationalEventType.EXECUTION_FAILED)
        .filter(e -> e.durationMs() != null && e.durationMs() >= 0)
        .forEach(e -> durations.put(e.executionId(), e.durationMs()));
    data.executions().stream()
        .filter(e -> RELIABILITY_TERMINAL.contains(e.state()))
        .filter(e -> e.startedAt() != null && completedAt(e) != null)
        .forEach(
            e ->
                durations.putIfAbsent(
                    e.executionId(), Duration.between(e.startedAt(), completedAt(e)).toMillis()));
    List<Long> sorted = durations.values().stream().filter(v -> v >= 0).sorted().toList();
    if (sorted.isEmpty()) {
      return new SliResult(
          1, EXECUTION_LATENCY_P95_MS, HealthDimensionCode.EXECUTION_LATENCY,
          SliStatus.INSUFFICIENT_DATA, null, "ms", 0, Map.of(), "Sem latências terminais");
    }
    double p50 = quantile(sorted, 0.50);
    double p95 = quantile(sorted, 0.95);
    return new SliResult(
        1, EXECUTION_LATENCY_P95_MS, HealthDimensionCode.EXECUTION_LATENCY,
        SliStatus.AVAILABLE, p95, "ms", sorted.size(),
        Map.of("p50", p50, "p95", p95, "max", sorted.getLast().doubleValue()),
        "Latência técnica terminal");
  }

  private SliResult agedWaits(OperationalHealthData data, Duration threshold) {
    long aged =
        data.activeWaits().stream()
            .filter(wait -> !wait.createdAt().plus(threshold).isAfter(clock.now()))
            .count();
    return ratio(
        ASYNC_WAIT_AGED, HealthDimensionCode.ASYNC_WAIT, aged, data.activeWaits().size(),
        "Proporção de waits ativos com idade >= " + threshold);
  }

  private SliResult callbacks(OperationalHealthData data) {
    long eligible =
        data.callbacks().stream()
            .filter(
                c ->
                    c.state() == CallbackOutboxState.DELIVERED
                        || c.state() == CallbackOutboxState.DEAD_LETTERED
                        || c.state() == CallbackOutboxState.EXPIRED
                        || c.state() == CallbackOutboxState.CANCELLED)
            .count();
    long delivered =
        data.callbacks().stream().filter(c -> c.state() == CallbackOutboxState.DELIVERED).count();
    return ratio(
        CALLBACK_CONFIRMATION_RATIO, HealthDimensionCode.CALLBACK_DELIVERY, delivered, eligible,
        "DELIVERED entre callbacks com estado terminal");
  }

  private SliResult signals(OperationalHealthData data) {
    long accepted =
        data.events().stream()
            .filter(e -> e.eventType() == OperationalEventType.SIGNAL_ACCEPTED)
            .count();
    long rejected =
        data.events().stream()
            .filter(
                e ->
                    e.eventType() == OperationalEventType.SIGNAL_REJECTED
                        || e.eventType().name().startsWith("SECURITY_"))
            .count();
    return ratio(
        SIGNAL_ACCEPTANCE_RATIO, HealthDimensionCode.SIGNAL_INGRESS, accepted, accepted + rejected,
        "Sinais aceitos sobre aceitos e rejeitados");
  }

  private SliResult telemetryCoverage(OperationalHealthData data) {
    Set<String> withEvents = new HashSet<>();
    data.events().forEach(e -> withEvents.add(e.executionId()));
    long covered =
        data.executions().stream().filter(e -> withEvents.contains(e.executionId())).count();
    return ratio(
        TELEMETRY_COVERAGE, HealthDimensionCode.TELEMETRY_COVERAGE, covered,
        data.executions().size(), "Execuções com ao menos um OperationalEvent");
  }

  private static SliResult ratio(
      String code, HealthDimensionCode dimension, long numerator, long denominator,
      String explanation) {
    if (denominator == 0) {
      return new SliResult(
          1, code, dimension, SliStatus.INSUFFICIENT_DATA, null, "ratio", 0,
          Map.of("numerator", (double) numerator, "denominator", 0d), explanation);
    }
    return new SliResult(
        1, code, dimension, SliStatus.AVAILABLE, numerator / (double) denominator, "ratio",
        denominator, Map.of("numerator", (double) numerator, "denominator", (double) denominator),
        explanation);
  }

  private static SliResult insufficient(SliDefinition definition, long sample, String reason) {
    return new SliResult(
        1, definition.code(), definition.dimension(), SliStatus.INSUFFICIENT_DATA, null,
        definition.unit(), sample, Map.of(), reason);
  }

  private static double quantile(List<Long> sorted, double quantile) {
    int index = Math.max(0, (int) Math.ceil(quantile * sorted.size()) - 1);
    return sorted.get(index);
  }

  private static ExecutionState terminalState(OperationalEventType type) {
    return switch (type) {
      case EXECUTION_SUCCEEDED -> ExecutionState.SUCCEEDED;
      case EXECUTION_FAILED -> ExecutionState.FAILED;
      case EXECUTION_REJECTED -> ExecutionState.REJECTED;
      case OUTBOUND_TIMEOUT -> ExecutionState.TIMED_OUT;
      default -> null;
    };
  }

  private static java.time.Instant completedAt(ExecutionControlRecord execution) {
    return execution.completedAt() != null ? execution.completedAt() : execution.lastUpdatedAt();
  }
}
