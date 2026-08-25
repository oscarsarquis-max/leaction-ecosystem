package br.com.banco.spider.operational.capacity;

import java.time.Instant;
import java.util.Objects;

/**
 * Pedido de admissão. Carrega apenas referências operacionais seguras — nunca conteúdo de negócio.
 */
public record AdmissionRequest(
    String operationRef,
    CapacityScopeType scopeType,
    String scopeRef,
    String workerType,
    String scheduleCode,
    String adapterBindingRef,
    String serviceClass,
    Instant requestedAt,
    String correlationRef) {

  public AdmissionRequest {
    Objects.requireNonNull(operationRef, "operationRef");
    scopeType = scopeType == null ? CapacityScopeType.GLOBAL : scopeType;
    scopeRef =
        scopeType == CapacityScopeType.GLOBAL || scopeRef == null || scopeRef.isBlank()
            ? CapacityScopeType.GLOBAL_SCOPE_REF
            : scopeRef.trim();
    Objects.requireNonNull(requestedAt, "requestedAt");
  }

  /** Referência do pedido para o escopo consultado, ou {@code null} quando o pedido não a declara. */
  public String refFor(CapacityScopeType type) {
    if (type == null) {
      return null;
    }
    if (type == scopeType) {
      return scopeRef;
    }
    return switch (type) {
      case GLOBAL -> CapacityScopeType.GLOBAL_SCOPE_REF;
      case SERVICE_CLASS -> serviceClass;
      case WORKER_TYPE -> workerType;
      case SCHEDULE -> scheduleCode;
      case ADAPTER_BINDING -> adapterBindingRef;
    };
  }

  public static AdmissionRequest forWorkerSchedule(
      String workerType,
      String scheduleCode,
      Instant requestedAt,
      String correlationRef) {
    return new AdmissionRequest(
        "worker-schedule:" + scheduleCode,
        CapacityScopeType.SCHEDULE,
        scheduleCode,
        workerType,
        scheduleCode,
        null,
        null,
        requestedAt,
        correlationRef);
  }
}
