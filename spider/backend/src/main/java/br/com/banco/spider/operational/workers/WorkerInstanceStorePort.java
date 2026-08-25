package br.com.banco.spider.operational.workers;

import java.time.Instant;
import java.util.List;
import java.util.Optional;

public interface WorkerInstanceStorePort {

  WorkerInstance upsert(WorkerInstance instance);

  Optional<WorkerInstance> findById(String workerId);

  List<WorkerInstance> findAll();

  List<WorkerInstance> findStale(Instant staleBefore);

  /** Transição condicional de estado; retorna vazio quando o estado observado divergiu. */
  Optional<WorkerInstance> compareAndSetStatus(
      String workerId,
      WorkerInstanceStatus expectedStatus,
      WorkerInstanceStatus newStatus,
      Instant now);
}
