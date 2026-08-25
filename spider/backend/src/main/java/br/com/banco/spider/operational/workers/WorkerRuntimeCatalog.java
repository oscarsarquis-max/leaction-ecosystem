package br.com.banco.spider.operational.workers;

import java.time.Duration;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

/**
 * Catálogo fechado de workers. Intervalos e códigos de agendamento são fixos no código: o runtime
 * não aceita definição arbitrária de trabalho vinda de configuração ou da borda.
 */
public final class WorkerRuntimeCatalog {

  public static final String SCHEDULE_DEFINITION_VERSION = "1.0";
  public static final int MAX_BATCH_SIZE = 100;

  private static final Map<WorkerType, Duration> INTERVALS = new EnumMap<>(WorkerType.class);
  private static final Map<WorkerType, String> SCHEDULE_CODES = new EnumMap<>(WorkerType.class);

  static {
    INTERVALS.put(WorkerType.SIGNAL_APPLICATION, Duration.ofSeconds(2));
    INTERVALS.put(WorkerType.WAIT_EXPIRY, Duration.ofSeconds(2));
    INTERVALS.put(WorkerType.CALLBACK_DELIVERY, Duration.ofSeconds(2));
    INTERVALS.put(WorkerType.CALLBACK_RECONCILIATION, Duration.ofSeconds(3));
    INTERVALS.put(WorkerType.CALLBACK_RECOVERY, Duration.ofSeconds(5));
    INTERVALS.put(WorkerType.SIGNAL_APPLICATION_RECOVERY, Duration.ofSeconds(5));
    INTERVALS.put(WorkerType.PROTECTED_ENVELOPE_MAINTENANCE, Duration.ofSeconds(30));

    SCHEDULE_CODES.put(WorkerType.SIGNAL_APPLICATION, "sched:signal-application@1");
    SCHEDULE_CODES.put(WorkerType.WAIT_EXPIRY, "sched:wait-expiry@1");
    SCHEDULE_CODES.put(WorkerType.CALLBACK_DELIVERY, "sched:callback-delivery@1");
    SCHEDULE_CODES.put(WorkerType.CALLBACK_RECONCILIATION, "sched:callback-reconciliation@1");
    SCHEDULE_CODES.put(WorkerType.CALLBACK_RECOVERY, "sched:callback-recovery@1");
    SCHEDULE_CODES.put(
        WorkerType.SIGNAL_APPLICATION_RECOVERY, "sched:signal-application-recovery@1");
    SCHEDULE_CODES.put(
        WorkerType.PROTECTED_ENVELOPE_MAINTENANCE, "sched:protected-envelope-maintenance@1");
  }

  private final List<WorkerTypeDefinition> definitions;
  private final Map<WorkerType, WorkerTypeDefinition> byType;
  private final Map<String, WorkerTypeDefinition> byScheduleCode;

  public WorkerRuntimeCatalog(
      int defaultBatchSize, Duration leaseDuration, Duration executionTimeout, int maxAttempts) {
    int batch = Math.max(1, Math.min(defaultBatchSize, MAX_BATCH_SIZE));
    Map<WorkerType, WorkerTypeDefinition> types = new EnumMap<>(WorkerType.class);
    for (WorkerType type : WorkerType.values()) {
      types.put(
          type,
          new WorkerTypeDefinition(
              type,
              SCHEDULE_CODES.get(type),
              SCHEDULE_DEFINITION_VERSION,
              INTERVALS.get(type),
              batch,
              leaseDuration,
              executionTimeout,
              maxAttempts,
              1));
    }
    this.byType = Map.copyOf(types);
    this.definitions = List.copyOf(types.values());
    this.byScheduleCode =
        this.definitions.stream()
            .collect(
                java.util.stream.Collectors.toUnmodifiableMap(
                    WorkerTypeDefinition::scheduleCode, definition -> definition));
  }

  public List<WorkerTypeDefinition> definitions() {
    return definitions;
  }

  public WorkerTypeDefinition definition(WorkerType type) {
    WorkerTypeDefinition definition = byType.get(type);
    if (definition == null) {
      throw new IllegalStateException("Unknown worker type: " + type);
    }
    return definition;
  }

  public Optional<WorkerTypeDefinition> byScheduleCode(String scheduleCode) {
    return scheduleCode == null ? Optional.empty() : Optional.ofNullable(byScheduleCode.get(scheduleCode));
  }

  public static String scheduleCode(WorkerType type) {
    return SCHEDULE_CODES.get(type);
  }
}
