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
import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerBacklogStatus;
import br.com.banco.spider.operational.workers.WorkerRuntimeQueryService;
import br.com.banco.spider.operational.workers.WorkerRuntimeSnapshot;
import br.com.banco.spider.operational.workers.WorkerRuntimeStatus;
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
  private final ObjectProvider<WorkerRuntimeQueryService> workerRuntimeProvider;

  public OperationalHealthQueryService(
      OperationalHealthProperties properties,
      SpiderClock clock,
      ProvisionalHealthDefinitionLoader loader,
      ObjectProvider<ExecutionControlStorePort> controlProvider,
      ObjectProvider<ExecutionWaitStorePort> waitProvider,
      ObjectProvider<CallbackOutboxStorePort> callbackProvider,
      ObjectProvider<OperationalEventStorePort> eventProvider,
      ObjectProvider<WorkerRuntimeQueryService> workerRuntimeProvider) {
    this.properties = properties;
    this.clock = clock;
    this.loader = loader;
    this.calculator = new ProvisionalSliCalculator(clock);
    this.controlProvider = controlProvider;
    this.waitProvider = waitProvider;
    this.callbackProvider = callbackProvider;
    this.eventProvider = eventProvider;
    this.workerRuntimeProvider = workerRuntimeProvider;
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
    dimensions.addAll(workerRuntimeDimensions());
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

  /**
   * Dimensões do runtime de workers. Quando o runtime está desligado nenhuma dimensão é acrescida —
   * a leitura de 017 permanece exatamente a mesma de antes de 019.
   */
  private List<HealthDimensionStatus> workerRuntimeDimensions() {
    WorkerRuntimeQueryService runtime = workerRuntimeProvider.getIfAvailable();
    if (runtime == null || !runtime.enabled()) {
      return List.of();
    }
    WorkerRuntimeSnapshot snapshot;
    try {
      snapshot = runtime.getSnapshot();
    } catch (RuntimeException unavailable) {
      return List.of();
    }
    if (snapshot.runtimeStatus() == WorkerRuntimeStatus.DISABLED) {
      return List.of();
    }
    List<HealthDimensionStatus> dimensions = new ArrayList<>();
    dimensions.add(
        dimension(
            HealthDimensionCode.WORKER_RUNTIME,
            switch (snapshot.runtimeStatus()) {
              case HEALTHY -> HealthStatus.HEALTHY;
              case DEGRADED, DRAINING -> HealthStatus.DEGRADED;
              case STOPPED -> HealthStatus.UNHEALTHY;
              case UNKNOWN, DISABLED -> HealthStatus.UNKNOWN;
            },
            "Runtime de workers em estado " + snapshot.runtimeStatus().name() + "."));

    boolean anyFailed =
        snapshot.schedules().stream()
            .anyMatch(schedule -> schedule.lastOutcome() == ScheduleOutcome.FAILED);
    dimensions.add(
        dimension(
            HealthDimensionCode.SCHEDULING,
            snapshot.schedules().isEmpty()
                ? HealthStatus.INSUFFICIENT_DATA
                : anyFailed ? HealthStatus.DEGRADED : HealthStatus.HEALTHY,
            snapshot.schedules().isEmpty()
                ? "Nenhum agendamento durável registrado na janela."
                : anyFailed
                    ? "Ao menos um agendamento terminou o último ciclo em falha."
                    : "Agendamentos duráveis concluindo os ciclos sem falha."));

    boolean backlogDegraded =
        snapshot.backlogs().stream()
            .anyMatch(
                backlog ->
                    backlog.status() == WorkerBacklogStatus.ACCUMULATING
                        || backlog.status() == WorkerBacklogStatus.STALE);
    boolean backlogUnknown =
        !snapshot.backlogs().isEmpty()
            && snapshot.backlogs().stream()
                .allMatch(backlog -> backlog.status() == WorkerBacklogStatus.UNKNOWN);
    dimensions.add(
        dimension(
            HealthDimensionCode.BACKLOG,
            snapshot.backlogs().isEmpty() || backlogUnknown
                ? HealthStatus.INSUFFICIENT_DATA
                : backlogDegraded ? HealthStatus.DEGRADED : HealthStatus.HEALTHY,
            backlogDegraded
                ? "Backlog acumulando ou envelhecido em ao menos um tipo de worker."
                : "Backlog dentro do esperado para os tipos de worker observados."));

    dimensions.add(
        dimension(
            HealthDimensionCode.LEASE_SAFETY,
            snapshot.expiredLeases() > 0 || snapshot.staleWorkers() > 0
                ? HealthStatus.DEGRADED
                : HealthStatus.HEALTHY,
            snapshot.expiredLeases() > 0 || snapshot.staleWorkers() > 0
                ? "Há leases vencidos ou workers sem sinal de vida recente."
                : "Nenhum lease vencido e nenhum worker sem sinal de vida."));
    return List.copyOf(dimensions);
  }

  private static HealthDimensionStatus dimension(
      HealthDimensionCode code, HealthStatus status, String explanation) {
    return new HealthDimensionStatus(1, code, status, List.of(), explanation);
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
            // Dimensões do runtime de workers não vêm dos SLIs provisórios.
            case WORKER_RUNTIME, SCHEDULING, BACKLOG, LEASE_SAFETY -> false;
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
