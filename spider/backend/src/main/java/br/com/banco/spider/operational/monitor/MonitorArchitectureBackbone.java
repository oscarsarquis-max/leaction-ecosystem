package br.com.banco.spider.operational.monitor;

import java.util.ArrayList;
import java.util.List;

/**
 * Architectural spine shared with Documentação → Arquitetura. Observed events mark
 * used components; the remainder stays visible as not used or not reached.
 */
public final class MonitorArchitectureBackbone {

  public static final String USED = "used";
  public static final String NOT_USED = "notUsed";
  public static final String NOT_REACHED = "notReached";
  public static final String STATE_NOT_USED = "not_used";
  public static final String STATE_NOT_REACHED = "not_reached";

  public enum PathRole {
    PATH,
    UNUSED_ON_SATELLITE
  }

  public record Slot(
      String stageId,
      String stageType,
      int sortOrder,
      String title,
      String macroStage,
      String componentCode,
      PathRole role,
      String unusedReason) {}

  private MonitorArchitectureBackbone() {}

  public static List<Slot> forKind(String kind) {
    if (MonitorProjectionRecord.KIND_SYNC.equals(kind)) {
      return syncSlots();
    }
    if (MonitorProjectionRecord.KIND_PAYMENT.equals(kind)) {
      return List.of();
    }
    return interactionSlots();
  }

  public static boolean unusedOnThisPath(Slot slot) {
    return slot != null && slot.role() == PathRole.UNUSED_ON_SATELLITE;
  }

  public static boolean usedState(String state) {
    if (state == null) {
      return false;
    }
    return switch (state) {
      case "completed", "rejected", "failed", "running", "waiting", "unknown" -> true;
      default -> false;
    };
  }

  public static String participationOf(String state) {
    if (STATE_NOT_USED.equals(state)) {
      return NOT_USED;
    }
    if (STATE_NOT_REACHED.equals(state)) {
      return NOT_REACHED;
    }
    return USED;
  }

  private static List<Slot> interactionSlots() {
    List<Slot> slots = new ArrayList<>();
    slots.add(path("received", "INTERACTION_RECEIVED", 10, "Satellite Interaction HTTP", "origin", "satellite-http"));
    slots.add(unused("canonical_http", 11, "Entrada canônica HTTP", "origin", "canonical-http",
        "Entrada canônica não utilizada nesta interação de satélite."));
    slots.add(unused("signal_http", 12, "Sinal HTTP", "origin", "signal-http",
        "Nenhum sinal HTTP nesta transação."));
    slots.add(unused("context_http", 13, "Aquisição contextual HTTP", "origin", "context-http",
        "Aquisição contextual HTTP não utilizada nesta transação."));
    slots.add(unused("contextual_link", 14, "Gateway contratual legado", "origin", "contextual-link",
        "Gateway contextual legado não utilizado nesta transação."));
    slots.add(path("authenticated", "SATELLITE_AUTHENTICATED", 20, "Satélite autenticado", "identity", "satellite-registry"));
    slots.add(path("replay_checked", "REPLAY_CHECK_PASSED", 22, "Replay e idempotência", "identity", "replay-guard"));
    slots.add(unused("canonical_ingress", 24, "Ingress canônico", "identity", "canonical-ingress-auth",
        "Ingress canônico não participa do Satellite Contract."));
    slots.add(path("contract_validated", "SATELLITE_CONTRACT_VALIDATED", 30, "Validação do contrato e contexto", "identity", "satellite-registry"));
    slots.add(path("company_authorized", "SATELLITE_COMPANY_AUTHORIZED", 40, "Empresa e policy", "identity", "satellite-registry"));
    slots.add(path("context_accepted", "SATELLITE_CONTEXT_ACCEPTED", 45, "Contexto e intenção", "context", "context-intelligence"));
    slots.add(unused("context_ai", 46, "Context Intelligence / IA", "context", "context-ai",
        "IA não utilizada nesta transação."));
    slots.add(path("objective_accepted", "SATELLITE_OBJECTIVE_ACCEPTED", 50, "Objetivo determinístico", "context", "context-intelligence"));
    slots.add(unused("execution_plan", 52, "Catálogo de Execution Plan", "plan", "execution-plan-catalog",
        "Execution Plan canônico não utilizado; a fatia financeira é determinística."));
    slots.add(unused("submit_canonical", 53, "SubmitCanonicalExecutionUseCase", "plan", "submit-canonical",
        "Submit canônico não utilizado nesta interação de satélite."));
    slots.add(unused("canonical_engine", 54, "Canonical Execution Engine", "plan", "canonical-engine",
        "Execution Engine canônica não utilizada nesta interação de satélite."));
    slots.add(path("capability_resolved", "CAPABILITY_RESOLVED", 60, "Capability LIST_EXTERNAL_PAYMENTS", "capabilities", "capability-catalog"));
    slots.add(path("route_selected", "ROUTE_RESOLVED", 70, "Rota ActionHub Pay", "resolution", "capability-catalog"));
    slots.add(path("request_sent", "OUTBOUND_REQUEST_STARTED", 80, "Adapter ActionHub Pay — solicitação", "execution", "provider-adapter"));
    slots.add(path("response_received", "PROVIDER_RESULT_RECEIVED", 90, "Adapter ActionHub Pay — resposta", "execution", "provider-adapter"));
    slots.add(unused("worker_runtime", 91, "Worker runtime", "execution", "worker-runtime",
        "Workers não utilizados nesta interação síncrona."));
    slots.add(unused("capacity_admission", 92, "Capacidade e bulkheads", "execution", "capacity-admission",
        "Admissão de capacidade de worker não utilizada."));
    slots.add(unused("mock_adapter", 93, "Mock Universal Adapter", "execution", "mock-universal-adapter",
        "Mock universal não utilizado; o adapter é o ActionHub Pay."));
    slots.add(unused("wait_signal", 94, "Wait, inbox e resume", "async", "wait-signal",
        "Espera/callback não utilizada nesta transação síncrona."));
    slots.add(unused("callback_outbox", 95, "Callback outbox", "async", "callback-outbox",
        "Callback/outbox não utilizado nesta transação."));
    slots.add(unused("callback_recon", 96, "Reconciliação de callback", "async", "callback-reconciliation",
        "Reconciliação de callback não utilizada nesta transação."));
    slots.add(path("result_recorded", "SATELLITE_DECISION_CREATED", 100, "Resultado registrado", "result", "satellite-registry"));
    slots.add(path("response_produced", "SATELLITE_RESPONSE_RETURNED", 110, "Resposta produzida", "result", "satellite-http"));
    slots.add(path("persistence_ports", "PROJECTIONS_UPSERTED", 200, "Ports de persistência", "observe", "persistence-ports"));
    slots.add(path("operational_events", "OPERATIONAL_EVENTS", 210, "Operational Event Store", "observe", "operational-events"));
    slots.add(path("monitor_query", "MONITOR_READ_MODEL", 220, "Monitor / read model", "observe", "monitor-query"));
    return slots;
  }

  private static List<Slot> syncSlots() {
    List<Slot> slots = new ArrayList<>();
    slots.add(path("sync_requested", "SYNC_REQUESTED", 10, "FinanceAction — origem", "origin", "satellite-http"));
    slots.add(unused("canonical_http", 11, "Entrada canônica HTTP", "origin", "canonical-http",
        "Entrada canônica não utilizada neste sincronismo."));
    slots.add(unused("signal_http", 12, "Sinal HTTP", "origin", "signal-http",
        "Nenhum sinal HTTP neste sincronismo."));
    slots.add(unused("context_http", 13, "Aquisição contextual HTTP", "origin", "context-http",
        "Aquisição contextual HTTP não utilizada neste sincronismo."));
    slots.add(unused("contextual_link", 14, "Gateway contratual legado", "origin", "contextual-link",
        "Gateway contextual legado não utilizado neste sincronismo."));
    slots.add(path("origin_authenticated", "SATELLITE_AUTHENTICATED", 20, "Satélite autenticado", "identity", "satellite-registry"));
    slots.add(path("replay_checked", "REPLAY_CHECK_PASSED", 22, "Replay e idempotência", "identity", "replay-guard"));
    slots.add(unused("canonical_ingress", 24, "Ingress canônico", "identity", "canonical-ingress-auth",
        "Ingress canônico não participa do Satellite Contract."));
    slots.add(path("contract_validated", "SATELLITE_CONTRACT_VALIDATED", 30, "Validação do contrato e contexto", "identity", "satellite-registry"));
    slots.add(path("company_authorized", "SATELLITE_COMPANY_AUTHORIZED", 35, "Empresa e policy", "identity", "satellite-registry"));
    slots.add(unused("context_ai", 38, "Context Intelligence / IA", "context", "context-ai",
        "IA não utilizada nesta transação."));
    slots.add(path("objective_accepted", "SATELLITE_OBJECTIVE_ACCEPTED", 40, "Objetivo determinístico", "context", "context-intelligence"));
    slots.add(unused("execution_plan", 42, "Catálogo de Execution Plan", "plan", "execution-plan-catalog",
        "Execution Plan canônico não utilizado; a listagem é determinística."));
    slots.add(unused("submit_canonical", 43, "SubmitCanonicalExecutionUseCase", "plan", "submit-canonical",
        "Submit canônico não utilizado neste sincronismo."));
    slots.add(unused("canonical_engine", 44, "Canonical Execution Engine", "plan", "canonical-engine",
        "Execution Engine canônica não utilizada neste sincronismo."));
    slots.add(path("listing_capability", "CAPABILITY_RESOLVED", 50, "Capability LIST_EXTERNAL_PAYMENTS", "capabilities", "capability-catalog"));
    slots.add(path("adapter_selected", "ROUTE_RESOLVED", 60, "Rota ActionHub Pay sandbox", "resolution", "capability-catalog"));
    slots.add(unused("worker_runtime", 91, "Worker runtime", "execution", "worker-runtime",
        "Workers não utilizados neste sincronismo síncrono."));
    slots.add(unused("capacity_admission", 92, "Capacidade e bulkheads", "execution", "capacity-admission",
        "Admissão de capacidade de worker não utilizada."));
    slots.add(unused("mock_adapter", 93, "Mock Universal Adapter", "execution", "mock-universal-adapter",
        "Mock universal não utilizado; o adapter é o ActionHub Pay."));
    slots.add(unused("wait_signal", 94, "Wait, inbox e resume", "async", "wait-signal",
        "Espera/callback não utilizada neste sincronismo síncrono."));
    slots.add(unused("callback_outbox", 95, "Callback outbox", "async", "callback-outbox",
        "Callback/outbox não utilizado neste sincronismo."));
    slots.add(unused("callback_recon", 96, "Reconciliação de callback", "async", "callback-reconciliation",
        "Reconciliação de callback não utilizada neste sincronismo."));
    slots.add(path("payments_correlated", "PAYMENTS_CORRELATED", 100, "Pagamentos correlacionados", "execution", "provider-adapter"));
    slots.add(path("projections_upserted", "PROJECTIONS_UPSERTED", 105, "Projeções persistidas", "observe", "persistence-ports"));
    slots.add(path("counts_recorded", "COUNTS_RECORDED", 108, "Contagens registradas", "result", "monitor-query"));
    slots.add(path("result_recorded", "SATELLITE_DECISION_CREATED", 110, "Resultado registrado", "result", "satellite-registry"));
    slots.add(path("sync_completed", "SATELLITE_RESPONSE_RETURNED", 120, "Resposta devolvida", "result", "satellite-http"));
    slots.add(path("operational_events", "OPERATIONAL_EVENTS", 210, "Operational Event Store", "observe", "operational-events"));
    slots.add(path("monitor_query", "MONITOR_READ_MODEL", 220, "Monitor / read model", "observe", "monitor-query"));
    return slots;
  }

  private static Slot path(
      String id, String type, int order, String title, String macro, String component) {
    return new Slot(id, type, order, title, macro, component, PathRole.PATH, null);
  }

  private static Slot unused(
      String id, int order, String title, String macro, String component, String reason) {
    return new Slot(id, "ARCHITECTURE_UNUSED", order, title, macro, component, PathRole.UNUSED_ON_SATELLITE, reason);
  }
}
