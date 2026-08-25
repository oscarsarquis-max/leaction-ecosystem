package br.com.banco.spider.operational.workers;

import java.util.Objects;

/**
 * Leitura de backlog por tipo de worker. {@code approximate} indica que a contagem veio de uma
 * consulta limitada — o runtime nunca faz varredura ilimitada só para contar.
 */
public record WorkerBacklogView(
    int schemaVersion,
    WorkerType workerType,
    WorkerBacklogStatus status,
    int eligibleCount,
    Long oldestEligibleAgeMs,
    boolean approximate,
    String explanation) {

  public static final int SCHEMA_VERSION = 1;

  public WorkerBacklogView {
    Objects.requireNonNull(workerType, "workerType");
    Objects.requireNonNull(status, "status");
    explanation = explanation == null ? "" : explanation;
  }

  public static WorkerBacklogView unknown(WorkerType workerType, String explanation) {
    return new WorkerBacklogView(
        SCHEMA_VERSION, workerType, WorkerBacklogStatus.UNKNOWN, 0, null, true, explanation);
  }
}
