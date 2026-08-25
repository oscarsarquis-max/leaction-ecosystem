package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.operational.workers.WorkerInstanceStatus;
import br.com.banco.spider.operational.workers.WorkerType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "tb_runtime_worker_instance")
public class RuntimeWorkerInstanceEntity {

  @Id
  @Column(name = "worker_id", length = 120)
  private String workerId;

  @Column(name = "runtime_instance_id", nullable = false, length = 120)
  private String runtimeInstanceId;

  @Enumerated(EnumType.STRING)
  @Column(name = "worker_type", nullable = false, length = 60)
  private WorkerType workerType;

  @Enumerated(EnumType.STRING)
  @Column(name = "status", nullable = false, length = 40)
  private WorkerInstanceStatus status;

  @Column(name = "started_at")
  private Instant startedAt;

  @Column(name = "last_heartbeat_at")
  private Instant lastHeartbeatAt;

  @Column(name = "drain_requested_at")
  private Instant drainRequestedAt;

  @Column(name = "stopped_at")
  private Instant stoppedAt;

  @Column(name = "current_claims", nullable = false)
  private int currentClaims;

  @Column(name = "processed_count", nullable = false)
  private long processedCount;

  @Column(name = "failure_count", nullable = false)
  private long failureCount;

  @Column(name = "version", nullable = false)
  private long version;

  public String getWorkerId() {
    return workerId;
  }

  public void setWorkerId(String workerId) {
    this.workerId = workerId;
  }

  public String getRuntimeInstanceId() {
    return runtimeInstanceId;
  }

  public void setRuntimeInstanceId(String runtimeInstanceId) {
    this.runtimeInstanceId = runtimeInstanceId;
  }

  public WorkerType getWorkerType() {
    return workerType;
  }

  public void setWorkerType(WorkerType workerType) {
    this.workerType = workerType;
  }

  public WorkerInstanceStatus getStatus() {
    return status;
  }

  public void setStatus(WorkerInstanceStatus status) {
    this.status = status;
  }

  public Instant getStartedAt() {
    return startedAt;
  }

  public void setStartedAt(Instant startedAt) {
    this.startedAt = startedAt;
  }

  public Instant getLastHeartbeatAt() {
    return lastHeartbeatAt;
  }

  public void setLastHeartbeatAt(Instant lastHeartbeatAt) {
    this.lastHeartbeatAt = lastHeartbeatAt;
  }

  public Instant getDrainRequestedAt() {
    return drainRequestedAt;
  }

  public void setDrainRequestedAt(Instant drainRequestedAt) {
    this.drainRequestedAt = drainRequestedAt;
  }

  public Instant getStoppedAt() {
    return stoppedAt;
  }

  public void setStoppedAt(Instant stoppedAt) {
    this.stoppedAt = stoppedAt;
  }

  public int getCurrentClaims() {
    return currentClaims;
  }

  public void setCurrentClaims(int currentClaims) {
    this.currentClaims = currentClaims;
  }

  public long getProcessedCount() {
    return processedCount;
  }

  public void setProcessedCount(long processedCount) {
    this.processedCount = processedCount;
  }

  public long getFailureCount() {
    return failureCount;
  }

  public void setFailureCount(long failureCount) {
    this.failureCount = failureCount;
  }

  public long getVersion() {
    return version;
  }

  public void setVersion(long version) {
    this.version = version;
  }
}
