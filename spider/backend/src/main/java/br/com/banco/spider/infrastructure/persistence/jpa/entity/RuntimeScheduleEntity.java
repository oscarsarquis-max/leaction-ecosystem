package br.com.banco.spider.infrastructure.persistence.jpa.entity;

import br.com.banco.spider.operational.workers.ScheduleOutcome;
import br.com.banco.spider.operational.workers.WorkerType;
import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

@Entity
@Table(name = "tb_runtime_schedule")
public class RuntimeScheduleEntity {

  @Id
  @Column(name = "schedule_code", length = 160)
  private String scheduleCode;

  @Column(name = "schedule_def_version", nullable = false, length = 20)
  private String scheduleDefVersion;

  @Enumerated(EnumType.STRING)
  @Column(name = "worker_type", nullable = false, length = 60)
  private WorkerType workerType;

  @Column(name = "enabled", nullable = false)
  private boolean enabled;

  @Column(name = "interval_seconds", nullable = false)
  private long intervalSeconds;

  @Column(name = "next_eligible_at", nullable = false)
  private Instant nextEligibleAt;

  @Column(name = "last_started_at")
  private Instant lastStartedAt;

  @Column(name = "last_completed_at")
  private Instant lastCompletedAt;

  @Enumerated(EnumType.STRING)
  @Column(name = "last_outcome", length = 40)
  private ScheduleOutcome lastOutcome;

  @Column(name = "owner_worker_id", length = 120)
  private String ownerWorkerId;

  @Column(name = "lease_until")
  private Instant leaseUntil;

  @Column(name = "fencing_token", nullable = false)
  private long fencingToken;

  @Column(name = "version", nullable = false)
  private long version;

  public String getScheduleCode() {
    return scheduleCode;
  }

  public void setScheduleCode(String scheduleCode) {
    this.scheduleCode = scheduleCode;
  }

  public String getScheduleDefVersion() {
    return scheduleDefVersion;
  }

  public void setScheduleDefVersion(String scheduleDefVersion) {
    this.scheduleDefVersion = scheduleDefVersion;
  }

  public WorkerType getWorkerType() {
    return workerType;
  }

  public void setWorkerType(WorkerType workerType) {
    this.workerType = workerType;
  }

  public boolean isEnabled() {
    return enabled;
  }

  public void setEnabled(boolean enabled) {
    this.enabled = enabled;
  }

  public long getIntervalSeconds() {
    return intervalSeconds;
  }

  public void setIntervalSeconds(long intervalSeconds) {
    this.intervalSeconds = intervalSeconds;
  }

  public Instant getNextEligibleAt() {
    return nextEligibleAt;
  }

  public void setNextEligibleAt(Instant nextEligibleAt) {
    this.nextEligibleAt = nextEligibleAt;
  }

  public Instant getLastStartedAt() {
    return lastStartedAt;
  }

  public void setLastStartedAt(Instant lastStartedAt) {
    this.lastStartedAt = lastStartedAt;
  }

  public Instant getLastCompletedAt() {
    return lastCompletedAt;
  }

  public void setLastCompletedAt(Instant lastCompletedAt) {
    this.lastCompletedAt = lastCompletedAt;
  }

  public ScheduleOutcome getLastOutcome() {
    return lastOutcome;
  }

  public void setLastOutcome(ScheduleOutcome lastOutcome) {
    this.lastOutcome = lastOutcome;
  }

  public String getOwnerWorkerId() {
    return ownerWorkerId;
  }

  public void setOwnerWorkerId(String ownerWorkerId) {
    this.ownerWorkerId = ownerWorkerId;
  }

  public Instant getLeaseUntil() {
    return leaseUntil;
  }

  public void setLeaseUntil(Instant leaseUntil) {
    this.leaseUntil = leaseUntil;
  }

  public long getFencingToken() {
    return fencingToken;
  }

  public void setFencingToken(long fencingToken) {
    this.fencingToken = fencingToken;
  }

  public long getVersion() {
    return version;
  }

  public void setVersion(long version) {
    this.version = version;
  }
}
