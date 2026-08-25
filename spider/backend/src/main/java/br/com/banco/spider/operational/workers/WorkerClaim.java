package br.com.banco.spider.operational.workers;

import java.time.Instant;
import java.util.Objects;

/** Resultado de um claim bem-sucedido: identifica o dono e o token de fencing daquele ciclo. */
public record WorkerClaim(
    String scheduleCode,
    WorkerType workerType,
    String workerId,
    long fencingToken,
    Instant claimedAt,
    Instant leaseUntil) {

  public WorkerClaim {
    Objects.requireNonNull(scheduleCode, "scheduleCode");
    Objects.requireNonNull(workerType, "workerType");
    Objects.requireNonNull(workerId, "workerId");
  }

  public static WorkerClaim of(DurableSchedule schedule, Instant claimedAt) {
    return new WorkerClaim(
        schedule.scheduleCode(),
        schedule.workerType(),
        schedule.ownerWorkerId(),
        schedule.fencingToken(),
        claimedAt,
        schedule.leaseUntil());
  }
}
