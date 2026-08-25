package br.com.banco.spider.operational.workers;

import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Telemetria do runtime de workers. Os eventos não pertencem a nenhuma execução de negócio, então
 * usam o identificador sintético {@value #RUNTIME_EXECUTION_ID} — documentado e reservado, nunca
 * confundível com um executionId canônico. Emissão é fail-open.
 */
public class WorkerRuntimeTelemetry {

  public static final String RUNTIME_EXECUTION_ID = "runtime:worker";
  public static final String SOURCE = "worker-runtime";

  private final ObjectProvider<OperationalEventPublisher> publisherProvider;

  public WorkerRuntimeTelemetry(ObjectProvider<OperationalEventPublisher> publisherProvider) {
    this.publisherProvider = publisherProvider;
  }

  public void emit(
      OperationalEventType type,
      WorkerType workerType,
      String scheduleCode,
      String reasonCode,
      OperationalEventOutcome outcome,
      Long durationMs) {
    OperationalEventPublisher publisher = publisherProvider.getIfAvailable();
    if (publisher == null) {
      return;
    }
    OperationalEventAttributes attributes =
        OperationalEventAttributes.builder()
            .component(SOURCE)
            .workerType(workerType == null ? null : workerType.name())
            .scheduleCode(scheduleCode)
            .reasonCode(reasonCode)
            .build();
    OperationalEventEmit.publish(
        publisher,
        OperationalEventEmit.draft(
            type, RUNTIME_EXECUTION_ID, null, SOURCE, outcome, durationMs, attributes));
  }

  public void emit(
      OperationalEventType type, WorkerType workerType, String scheduleCode, String reasonCode) {
    emit(type, workerType, scheduleCode, reasonCode, null, null);
  }
}
