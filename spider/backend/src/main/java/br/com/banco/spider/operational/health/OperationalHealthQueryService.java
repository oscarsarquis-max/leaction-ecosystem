package br.com.banco.spider.operational.health;

import br.com.banco.spider.config.OperationalHealthProperties;
import br.com.banco.spider.execution.callback.CallbackOutboxRecord;
import br.com.banco.spider.execution.persistence.model.ExecutionControlRecord;
import br.com.banco.spider.execution.persistence.port.CallbackOutboxStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionControlStorePort;
import br.com.banco.spider.execution.persistence.port.ExecutionWaitStorePort;
import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.execution.wait.ExecutionWaitRecord;
import br.com.banco.spider.operational.events.OperationalEvent;
import br.com.banco.spider.operational.events.OperationalEventStorePort;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.ObjectProvider;

public class OperationalHealthQueryService {
  private final OperationalHealthProperties properties;
  private final SpiderClock clock;
  private final ProvisionalHealthDefinitionLoader loader;
  private final ProvisionalSliCalculator calculator;
  private final ProvisionalSloEvaluator evaluator = new ProvisionalSloEvaluator();
  private final OperationalHealthAggregator aggregator = new OperationalHealthAggregator();
  private final ObjectProvider<ExecutionControlStorePort> controlProvider;
  private final ObjectProvider<ExecutionWaitStorePort> waitProvider;
  private final ObjectProvider<CallbackOutboxStorePort> callbackProvider;
  private final ObjectProvider<OperationalEventStorePort> eventProvider;

  public OperationalHealthQueryService(
      OperationalHealthProperties properties,
      SpiderClock clock,
      ProvisionalHealthDefinitionLoader loader,
      ObjectProvider<ExecutionControlStorePort> controlProvider,
      ObjectProvider<ExecutionWaitStorePort> waitProvider,
      ObjectProvider<CallbackOutboxStorePort> callbackProvider,
      ObjectProvider<OperationalEventStorePort> eventProvider) {
    this.properties = properties;
    this.clock = clock;
    this.loader = loader;
    this.calculator = new ProvisionalSliCalculator(clock);
    this.controlProvider = controlProvider;
    this.waitProvider = waitProvider;
    this.callbackProvider = callbackProvider;
    this.eventProvider = eventProvider;
  }

  public OperationalHealthSnapshot getSnapshot(String requestedWindow) {
    Duration duration =
        requestedWindow == null || requestedWindow.isBlank()
            ? properties.getDefaultWindow()
            : parseWindow(requestedWindow);
    if (!properties.getAllowedWindows().contains(duration)
        || duration.compareTo(properties.getMaxWindow()) > 0) {
      throw new IllegalArgumentException("Window is not allowed: " + duration);
    }
    Instant now = clock.now();
    OperationalHealthWindow window = OperationalHealthWindow.endingAt(now, duration);
    int limit = properties.getMaxResults();
    List<String> available = new ArrayList<>();
    List<String> missing = new ArrayList<>();

    ExecutionControlStorePort control = controlProvider.getIfAvailable();
    List<ExecutionControlRecord> executions =
        control == null
            ? missing("executionControlStore", missing)
            : available(
                "executionControlStore",
                available,
                control.listStartedBetween(window.from(), window.to(), limit));
    ExecutionWaitStorePort wait = waitProvider.getIfAvailable();
    List<ExecutionWaitRecord> waits =
        wait == null
            ? missing("executionWaitStore", missing)
            : available("executionWaitStore", available, wait.listActive(limit));
    CallbackOutboxStorePort callback = callbackProvider.getIfAvailable();
    List<CallbackOutboxRecord> callbacks =
        callback == null
            ? missing("callbackOutboxStore", missing)
            : available("callbackOutboxStore", available, callback.listAllBounded(limit));
    OperationalEventStorePort event = eventProvider.getIfAvailable();
    List<OperationalEvent> events =
        event == null
            ? missing("operationalEventStore", missing)
            : available(
                "operationalEventStore",
                available,
                event.findOccurredBetween(window.from(), window.to(), limit));

    List<SliDefinition> effectiveDefinitions =
        loader.definitions().stream()
            .map(
                definition ->
                    new SliDefinition(
                        definition.schemaVersion(),
                        definition.code(),
                        definition.version(),
                        definition.title(),
                        definition.functionalDescription(),
                        definition.dimension(),
                        definition.unit(),
                        Math.max(
                            definition.minimumSampleSize(), properties.getMinimumSampleSize()),
                        definition.higherIsBetter(),
                        definition.reliabilityStyle()))
            .toList();
    List<SliResult> slis =
        calculator.calculate(
            effectiveDefinitions,
            new OperationalHealthData(executions, waits, callbacks, events),
            properties.getAgedWaitThreshold());
    slis = markMissingSources(slis, control, wait, callback, event);
    Map<String, SliResult> byCode =
        slis.stream().collect(java.util.stream.Collectors.toMap(SliResult::code, s -> s));
    List<SloEvaluation> slos = new ArrayList<>();
    List<ErrorBudgetEvaluation> budgets = new ArrayList<>();
    List<HealthDimensionStatus> dimensions = new ArrayList<>();
    for (ProvisionalSloObjective objective : loader.profile().objectives()) {
      SliResult sli = byCode.get(objective.sliCode());
      if (sli == null) {
        continue;
      }
      SloEvaluation slo = evaluator.evaluate(sli, objective);
      slos.add(slo);
      budgets.add(evaluator.evaluateErrorBudget(sli, objective));
      dimensions.add(
          new HealthDimensionStatus(
              1, sli.dimension(), toHealthStatus(slo.status()), List.of(sli.code()),
              slo.explanation()));
    }
    boolean capped =
        executions.size() == limit
            || waits.size() == limit
            || callbacks.size() == limit
            || events.size() == limit;
    DataQualitySummary quality =
        new DataQualitySummary(
            1, missing.isEmpty() && !capped, capped, available, missing,
            capped ? List.of("At least one bounded query reached maxResults=" + limit) : List.of());
    return new OperationalHealthSnapshot(
        1, now, loader.profile().integrationLevel(), loader.profile().provisional(),
        aggregator.aggregate(dimensions), window, slis, slos, budgets, dimensions, quality);
  }

  public Map<String, Object> definitions() {
    return Map.of("definitions", loader.definitions(), "profile", loader.profile());
  }

  private Duration parseWindow(String value) {
    try {
      return Duration.parse(value);
    } catch (RuntimeException invalid) {
      throw new IllegalArgumentException("Window must be an ISO-8601 duration", invalid);
    }
  }

  private static List<SliResult> markMissingSources(
      List<SliResult> input,
      ExecutionControlStorePort controls,
      ExecutionWaitStorePort waits,
      CallbackOutboxStorePort callbacks,
      OperationalEventStorePort events) {
    List<SliResult> output = new ArrayList<>();
    for (SliResult result : input) {
      boolean missing =
          switch (result.dimension()) {
            case EXECUTION_FLOW, EXECUTION_LATENCY -> controls == null && events == null;
            case ASYNC_WAIT -> waits == null;
            case CALLBACK_DELIVERY -> callbacks == null;
            case SIGNAL_INGRESS -> events == null;
            case TELEMETRY_COVERAGE -> controls == null || events == null;
          };
      output.add(
          missing
              ? new SliResult(
                  1, result.code(), result.dimension(), SliStatus.INSUFFICIENT_DATA, null,
                  result.unit(), 0, Map.of(), "Fonte canônica necessária indisponível")
              : result);
    }
    return List.copyOf(output);
  }

  private static HealthStatus toHealthStatus(SloComplianceStatus status) {
    return switch (status) {
      case MET -> HealthStatus.HEALTHY;
      case AT_RISK -> HealthStatus.DEGRADED;
      case MISSED -> HealthStatus.UNHEALTHY;
      case INSUFFICIENT_DATA -> HealthStatus.INSUFFICIENT_DATA;
      case UNKNOWN -> HealthStatus.UNKNOWN;
    };
  }

  private static <T> List<T> missing(String source, List<String> missing) {
    missing.add(source);
    return List.of();
  }

  private static <T> List<T> available(String source, List<String> available, List<T> values) {
    available.add(source);
    return values;
  }
}
