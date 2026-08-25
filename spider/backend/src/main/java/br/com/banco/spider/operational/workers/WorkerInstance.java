package br.com.banco.spider.operational.workers;

import java.time.Instant;
import java.util.Objects;

public record WorkerInstance(
    String workerId,
    String runtimeInstanceId,
    WorkerType workerType,
    WorkerInstanceStatus status,
    Instant startedAt,
    Instant lastHeartbeatAt,
    Instant drainRequestedAt,
    Instant stoppedAt,
    int currentClaims,
    long processedCount,
    long failureCount,
    long version) {

  public WorkerInstance {
    Objects.requireNonNull(workerId, "workerId");
    Objects.requireNonNull(runtimeInstanceId, "runtimeInstanceId");
    Objects.requireNonNull(workerType, "workerType");
    Objects.requireNonNull(status, "status");
  }

  public static WorkerInstance starting(
      String workerId, String runtimeInstanceId, WorkerType workerType, Instant now) {
    return new WorkerInstance(
        workerId,
        runtimeInstanceId,
        workerType,
        WorkerInstanceStatus.STARTING,
        now,
        now,
        null,
        null,
        0,
        0L,
        0L,
        0L);
  }

  public WorkerInstance withStatus(WorkerInstanceStatus newStatus, Instant now) {
    return new WorkerInstance(
        workerId,
        runtimeInstanceId,
        workerType,
        newStatus,
        startedAt,
        lastHeartbeatAt,
        drainRequestedAt,
        newStatus == WorkerInstanceStatus.STOPPED ? now : stoppedAt,
        currentClaims,
        processedCount,
        failureCount,
        version + 1);
  }

  public WorkerInstance withHeartbeat(Instant now) {
    return new WorkerInstance(
        workerId,
        runtimeInstanceId,
        workerType,
        status,
        startedAt,
        now,
        drainRequestedAt,
        stoppedAt,
        currentClaims,
        processedCount,
        failureCount,
        version + 1);
  }

  public WorkerInstance withDrainRequested(Instant now) {
    return new WorkerInstance(
        workerId,
        runtimeInstanceId,
        workerType,
        WorkerInstanceStatus.DRAINING,
        startedAt,
        lastHeartbeatAt,
        now,
        stoppedAt,
        currentClaims,
        processedCount,
        failureCount,
        version + 1);
  }

  public WorkerInstance withClaims(int claims) {
    return new WorkerInstance(
        workerId,
        runtimeInstanceId,
        workerType,
        status,
        startedAt,
        lastHeartbeatAt,
        drainRequestedAt,
        stoppedAt,
        Math.max(0, claims),
        processedCount,
        failureCount,
        version + 1);
  }

  public WorkerInstance withCounters(long processedDelta, long failureDelta) {
    return new WorkerInstance(
        workerId,
        runtimeInstanceId,
        workerType,
        status,
        startedAt,
        lastHeartbeatAt,
        drainRequestedAt,
        stoppedAt,
        currentClaims,
        processedCount + Math.max(0, processedDelta),
        failureCount + Math.max(0, failureDelta),
        version + 1);
  }

  public boolean draining() {
    return status == WorkerInstanceStatus.DRAINING;
  }
}
