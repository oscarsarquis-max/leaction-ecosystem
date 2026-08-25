package br.com.banco.spider.operational.capacity;

import br.com.banco.spider.operational.events.OperationalEventAttributes;
import br.com.banco.spider.operational.events.OperationalEventEmit;
import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventPublisher;
import br.com.banco.spider.operational.events.OperationalEventType;
import org.springframework.beans.factory.ObjectProvider;

/**
 * Telemetria do governo de capacidade. Os eventos não pertencem a nenhuma execução de negócio, então
 * usam o identificador sintético {@value #CAPACITY_EXECUTION_ID} — reservado e documentado. Emissão
 * é fail-open: nenhuma decisão de admissão depende da telemetria ter sido registrada.
 */
public class CapacityTelemetry {

  public static final String CAPACITY_EXECUTION_ID = "runtime:capacity";
  public static final String SOURCE = "capacity-governance";

  private final ObjectProvider<OperationalEventPublisher> publisherProvider;

  public CapacityTelemetry(ObjectProvider<OperationalEventPublisher> publisherProvider) {
    this.publisherProvider = publisherProvider;
  }

  public void emitDecision(AdmissionDecision decision) {
    OperationalEventType type =
        switch (decision.result()) {
          case ADMITTED, DELAYED -> OperationalEventType.CAPACITY_ADMISSION_ADMITTED;
          case SHED -> OperationalEventType.CAPACITY_ADMISSION_SHED;
          case REJECTED_QUOTA, REJECTED_CAPACITY, REJECTED_CIRCUIT_OPEN ->
              OperationalEventType.CAPACITY_ADMISSION_REJECTED;
        };
    OperationalEventOutcome outcome =
        decision.result().admitted() || decision.monitorOnly()
            ? OperationalEventOutcome.INFO
            : OperationalEventOutcome.REJECTED;
    emit(
        type,
        outcome,
        decision.reasonCode(),
        decision.policyRef(),
        decision.scopeKey(),
        decision.result().name(),
        null);
  }

  public void emitShed(AdmissionDecision decision, ShedReason reason) {
    emit(
        OperationalEventType.CAPACITY_LOAD_SHED,
        OperationalEventOutcome.REJECTED,
        reason.name(),
        decision.policyRef(),
        decision.scopeKey(),
        AdmissionResult.SHED.name(),
        null);
  }

  public void emitBulkheadSaturated(String scopeKey, String policyRef) {
    emit(
        OperationalEventType.CAPACITY_BULKHEAD_SATURATED,
        OperationalEventOutcome.REJECTED,
        ShedReason.CONCURRENCY_EXHAUSTED.name(),
        policyRef,
        scopeKey,
        null,
        null);
  }

  public void emitQuotaExhausted(String scopeKey, String policyRef) {
    emit(
        OperationalEventType.CAPACITY_QUOTA_EXHAUSTED,
        OperationalEventOutcome.REJECTED,
        ShedReason.QUOTA_EXHAUSTED.name(),
        policyRef,
        scopeKey,
        null,
        null);
  }

  public void emitCircuitTransition(String scopeKey, CircuitPhase phase, String reasonCode) {
    OperationalEventType type =
        switch (phase) {
          case OPEN -> OperationalEventType.CAPACITY_CIRCUIT_OPENED;
          case HALF_OPEN -> OperationalEventType.CAPACITY_CIRCUIT_HALF_OPEN;
          case CLOSED -> OperationalEventType.CAPACITY_CIRCUIT_CLOSED;
        };
    emit(
        type,
        phase == CircuitPhase.CLOSED
            ? OperationalEventOutcome.INFO
            : OperationalEventOutcome.REJECTED,
        reasonCode,
        null,
        scopeKey,
        null,
        phase.name());
  }

  private void emit(
      OperationalEventType type,
      OperationalEventOutcome outcome,
      String reasonCode,
      String policyRef,
      String capacityScope,
      String admissionResult,
      String circuitPhase) {
    OperationalEventPublisher publisher = publisherProvider.getIfAvailable();
    if (publisher == null) {
      return;
    }
    OperationalEventAttributes attributes =
        OperationalEventAttributes.builder()
            .component(SOURCE)
            .reasonCode(reasonCode)
            .policyRef(policyRef)
            .capacityScope(capacityScope)
            .admissionResult(admissionResult)
            .circuitPhase(circuitPhase)
            .build();
    OperationalEventEmit.publish(
        publisher,
        OperationalEventEmit.draft(
            type, CAPACITY_EXECUTION_ID, null, SOURCE, outcome, null, attributes));
  }
}
