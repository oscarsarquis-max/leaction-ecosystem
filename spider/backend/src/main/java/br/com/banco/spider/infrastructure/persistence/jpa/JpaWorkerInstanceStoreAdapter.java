package br.com.banco.spider.infrastructure.persistence.jpa;

import br.com.banco.spider.infrastructure.persistence.jpa.entity.RuntimeWorkerInstanceEntity;
import br.com.banco.spider.infrastructure.persistence.jpa.repository.RuntimeWorkerInstanceJpaRepository;
import br.com.banco.spider.operational.workers.WorkerInstance;
import br.com.banco.spider.operational.workers.WorkerInstanceStatus;
import br.com.banco.spider.operational.workers.WorkerInstanceStorePort;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.transaction.annotation.Transactional;

public class JpaWorkerInstanceStoreAdapter implements WorkerInstanceStorePort {

  private static final List<WorkerInstanceStatus> ACTIVE =
      List.of(
          WorkerInstanceStatus.STARTING, WorkerInstanceStatus.IDLE, WorkerInstanceStatus.RUNNING);

  private final RuntimeWorkerInstanceJpaRepository repo;

  public JpaWorkerInstanceStoreAdapter(RuntimeWorkerInstanceJpaRepository repo) {
    this.repo = repo;
  }

  @Override
  @Transactional
  public WorkerInstance upsert(WorkerInstance instance) {
    return toModel(repo.save(toEntity(instance)));
  }

  @Override
  @Transactional(readOnly = true)
  public Optional<WorkerInstance> findById(String workerId) {
    return workerId == null ? Optional.empty() : repo.findById(workerId).map(this::toModel);
  }

  @Override
  @Transactional(readOnly = true)
  public List<WorkerInstance> findAll() {
    return repo.findAll().stream()
        .sorted(java.util.Comparator.comparing(RuntimeWorkerInstanceEntity::getWorkerId))
        .map(this::toModel)
        .toList();
  }

  @Override
  @Transactional(readOnly = true)
  public List<WorkerInstance> findStale(Instant staleBefore) {
    return repo.findStale(ACTIVE, staleBefore).stream().map(this::toModel).toList();
  }

  @Override
  @Transactional
  public Optional<WorkerInstance> compareAndSetStatus(
      String workerId,
      WorkerInstanceStatus expectedStatus,
      WorkerInstanceStatus newStatus,
      Instant now) {
    Optional<RuntimeWorkerInstanceEntity> current = repo.findById(workerId);
    if (current.isEmpty()) {
      return Optional.empty();
    }
    WorkerInstanceStatus expected =
        expectedStatus == null ? current.get().getStatus() : expectedStatus;
    Instant stoppedAt =
        newStatus == WorkerInstanceStatus.STOPPED ? now : current.get().getStoppedAt();
    int updated = repo.compareAndSetStatus(workerId, expected, newStatus, stoppedAt, now);
    if (updated == 0) {
      return Optional.empty();
    }
    return repo.findById(workerId).map(this::toModel);
  }

  private RuntimeWorkerInstanceEntity toEntity(WorkerInstance instance) {
    RuntimeWorkerInstanceEntity e = new RuntimeWorkerInstanceEntity();
    e.setWorkerId(instance.workerId());
    e.setRuntimeInstanceId(instance.runtimeInstanceId());
    e.setWorkerType(instance.workerType());
    e.setStatus(instance.status());
    e.setStartedAt(instance.startedAt());
    e.setLastHeartbeatAt(instance.lastHeartbeatAt());
    e.setDrainRequestedAt(instance.drainRequestedAt());
    e.setStoppedAt(instance.stoppedAt());
    e.setCurrentClaims(instance.currentClaims());
    e.setProcessedCount(instance.processedCount());
    e.setFailureCount(instance.failureCount());
    e.setVersion(instance.version());
    return e;
  }

  private WorkerInstance toModel(RuntimeWorkerInstanceEntity e) {
    return new WorkerInstance(
        e.getWorkerId(),
        e.getRuntimeInstanceId(),
        e.getWorkerType(),
        e.getStatus(),
        e.getStartedAt(),
        e.getLastHeartbeatAt(),
        e.getDrainRequestedAt(),
        e.getStoppedAt(),
        e.getCurrentClaims(),
        e.getProcessedCount(),
        e.getFailureCount(),
        e.getVersion());
  }
}
