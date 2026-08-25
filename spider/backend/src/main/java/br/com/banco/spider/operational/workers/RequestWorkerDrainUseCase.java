package br.com.banco.spider.operational.workers;

import br.com.banco.spider.execution.support.SpiderClock;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.time.Instant;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Marca um worker para drenagem. Não interrompe o ciclo em curso e não remove leases: a posse
 * continua expirando por tempo, como em qualquer outro caminho do runtime.
 */
public class RequestWorkerDrainUseCase {

  private static final Logger log = LoggerFactory.getLogger(RequestWorkerDrainUseCase.class);

  private final WorkerInstanceStorePort instanceStore;
  private final WorkerRuntimeCatalog catalog;
  private final WorkerRuntimeTelemetry telemetry;
  private final SpiderClock clock;

  public RequestWorkerDrainUseCase(
      WorkerInstanceStorePort instanceStore,
      WorkerRuntimeCatalog catalog,
      WorkerRuntimeTelemetry telemetry,
      SpiderClock clock) {
    this.instanceStore = instanceStore;
    this.catalog = catalog;
    this.telemetry = telemetry;
    this.clock = clock;
  }

  public Optional<WorkerInstance> requestDrain(String workerId, String requestedBy) {
    Instant now = clock.now();
    Optional<WorkerInstance> current = instanceStore.findById(workerId);
    if (current.isEmpty()) {
      return Optional.empty();
    }
    WorkerInstance worker = current.get();
    if (worker.status() == WorkerInstanceStatus.STOPPED) {
      return Optional.of(worker);
    }
    WorkerInstance draining = instanceStore.upsert(worker.withDrainRequested(now));
    telemetry.emit(
        OperationalEventType.WORKER_DRAIN_REQUESTED,
        draining.workerType(),
        catalog.definition(draining.workerType()).scheduleCode(),
        "DRAIN_REQUESTED");
    log.info(
        "event=worker_drain_requested workerId={} workerType={} requestedBy={}",
        workerId,
        draining.workerType(),
        requestedBy == null ? "unknown" : requestedBy);
    return Optional.of(draining);
  }
}
