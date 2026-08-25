package br.com.banco.spider.infrastructure.persistence.memory;

import br.com.banco.spider.operational.workers.WorkerInstance;
import br.com.banco.spider.operational.workers.WorkerInstanceStatus;
import br.com.banco.spider.operational.workers.WorkerInstanceStorePort;
import java.time.Instant;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

public class InMemoryWorkerInstanceStore implements WorkerInstanceStorePort {

  private final Map<String, WorkerInstance> byId = new ConcurrentHashMap<>();

  @Override
  public WorkerInstance upsert(WorkerInstance instance) {
    byId.put(instance.workerId(), instance);
    return instance;
  }

  @Override
  public Optional<WorkerInstance> findById(String workerId) {
    return workerId == null ? Optional.empty() : Optional.ofNullable(byId.get(workerId));
  }

  @Override
  public List<WorkerInstance> findAll() {
    return byId.values().stream()
        .sorted(Comparator.comparing(WorkerInstance::workerId))
        .toList();
  }

  @Override
  public List<WorkerInstance> findStale(Instant staleBefore) {
    return byId.values().stream()
        .filter(instance -> instance.status().active())
        .filter(
            instance ->
                instance.lastHeartbeatAt() == null
                    || instance.lastHeartbeatAt().isBefore(staleBefore))
        .sorted(Comparator.comparing(WorkerInstance::workerId))
        .toList();
  }

  @Override
  public synchronized Optional<WorkerInstance> compareAndSetStatus(
      String workerId,
      WorkerInstanceStatus expectedStatus,
      WorkerInstanceStatus newStatus,
      Instant now) {
    WorkerInstance current = byId.get(workerId);
    if (current == null) {
      return Optional.empty();
    }
    if (expectedStatus != null && current.status() != expectedStatus) {
      return Optional.empty();
    }
    WorkerInstance updated = current.withStatus(newStatus, now).withHeartbeat(now);
    byId.put(workerId, updated);
    return Optional.of(updated);
  }
}
