package br.com.banco.spider.operational.monitor;

import br.com.banco.spider.operational.events.OperationalEventOutcome;
import br.com.banco.spider.operational.events.OperationalEventType;
import java.util.Locale;
import java.util.Set;

public final class MonitorJourneyCatalog {

  private static final Set<String> TERMINAL_STAGE_IDS =
      Set.of("response_produced", "sync_completed", "financial_state", "result_recorded");

  private MonitorJourneyCatalog() {}

  public record Binding(
      String stageId, String stageType, int sortOrder, String title, String definitionKey, String componentCode) {}

  public static Binding forEvent(String kind, OperationalEventType type, Integer page, String reason) {
    if (type == null) {
      return null;
    }
    if (MonitorProjectionRecord.KIND_SYNC.equals(kind)) {
      return forSync(type, page);
    }
    if (MonitorProjectionRecord.KIND_PAYMENT.equals(kind)) {
      return null;
    }
    return forInteraction(type);
  }

  public static Binding forInteraction(OperationalEventType type) {
    return switch (type) {
      case SATELLITE_REQUEST_RECEIVED ->
          bind("received", "INTERACTION_RECEIVED", 10, "Satellite Interaction HTTP", "origin", "satellite-http");
      case SATELLITE_AUTHENTICATED ->
          bind("authenticated", "SATELLITE_AUTHENTICATED", 20, "Satélite autenticado", "identity", "satellite-registry");
      case SATELLITE_CONTRACT_VALIDATED ->
          bind(
              "contract_validated",
              "SATELLITE_CONTRACT_VALIDATED",
              30,
              "Validação do contrato e contexto",
              "identity",
              "satellite-registry");
      case SATELLITE_COMPANY_AUTHORIZED ->
          bind("company_authorized", "SATELLITE_COMPANY_AUTHORIZED", 40, "Empresa e policy", "identity", "satellite-registry");
      case SATELLITE_OBJECTIVE_ACCEPTED ->
          bind("objective_accepted", "SATELLITE_OBJECTIVE_ACCEPTED", 50, "Objetivo determinístico", "context", "context-intelligence");
      case SATELLITE_CONTEXT_ACCEPTED ->
          bind("context_accepted", "SATELLITE_CONTEXT_ACCEPTED", 45, "Contexto e intenção", "context", "context-intelligence");
      case CAPABILITY_RESOLVED, CAPABILITY_DISPATCHED ->
          bind("capability_resolved", type.name(), 60, "Capability LIST_EXTERNAL_PAYMENTS", "capabilities", "capability-catalog");
      case CAPABILITY_UNAVAILABLE ->
          bind("capability_resolved", "CAPABILITY_UNAVAILABLE", 60, "Capability indisponível", "capabilities", "capability-catalog");
      case ROUTE_RESOLVED ->
          bind("route_selected", "ROUTE_RESOLVED", 70, "Rota ActionHub Pay", "resolution", "capability-catalog");
      case OUTBOUND_REQUEST_STARTED ->
          bind("request_sent", "OUTBOUND_REQUEST_STARTED", 80, "Adapter ActionHub Pay — solicitação", "execution", "provider-adapter");
      case OUTBOUND_RESPONSE_RECEIVED, PROVIDER_RESULT_RECEIVED ->
          bind("response_received", type.name(), 90, "Adapter ActionHub Pay — resposta", "execution", "provider-adapter");
      case OUTBOUND_TIMEOUT, OUTBOUND_TRANSPORT_ERROR ->
          bind("response_received", type.name(), 90, "Resposta não confirmada", "execution", "provider-adapter");
      case SATELLITE_DECISION_CREATED ->
          bind("result_recorded", "SATELLITE_DECISION_CREATED", 100, "Resultado registrado", "result", "satellite-registry");
      case SATELLITE_RESPONSE_RETURNED ->
          bind("response_produced", "SATELLITE_RESPONSE_RETURNED", 110, "Resposta produzida", "result", "satellite-http");
      default -> null;
    };
  }

  public static Binding forSync(OperationalEventType type, Integer page) {
    return switch (type) {
      case SATELLITE_REQUEST_RECEIVED ->
          bind("sync_requested", "SYNC_REQUESTED", 10, "FinanceAction — origem", "origin", "satellite-http");
      case SATELLITE_AUTHENTICATED ->
          bind("origin_authenticated", "SATELLITE_AUTHENTICATED", 20, "Satélite autenticado", "identity", "satellite-registry");
      case SATELLITE_CONTRACT_VALIDATED ->
          bind(
              "contract_validated",
              "SATELLITE_CONTRACT_VALIDATED",
              30,
              "Validação do contrato e contexto",
              "identity",
              "satellite-registry");
      case SATELLITE_COMPANY_AUTHORIZED ->
          bind("company_authorized", "SATELLITE_COMPANY_AUTHORIZED", 35, "Empresa e policy", "identity", "satellite-registry");
      case SATELLITE_OBJECTIVE_ACCEPTED ->
          bind("objective_accepted", "SATELLITE_OBJECTIVE_ACCEPTED", 40, "Objetivo determinístico", "context", "context-intelligence");
      case CAPABILITY_RESOLVED, CAPABILITY_DISPATCHED ->
          bind("listing_capability", type.name(), 50, "Capability LIST_EXTERNAL_PAYMENTS", "capabilities", "capability-catalog");
      case CAPABILITY_UNAVAILABLE ->
          bind("listing_capability", "CAPABILITY_UNAVAILABLE", 50, "Capability de listagem indisponível", "capabilities", "capability-catalog");
      case ROUTE_RESOLVED ->
          bind("adapter_selected", "ROUTE_RESOLVED", 60, "Rota ActionHub Pay sandbox", "resolution", "capability-catalog");
      case OUTBOUND_REQUEST_STARTED -> pageBinding(page, false);
      case OUTBOUND_RESPONSE_RECEIVED, PROVIDER_RESULT_RECEIVED -> pageBinding(page, true);
      case OUTBOUND_TIMEOUT, OUTBOUND_TRANSPORT_ERROR ->
          bind("response_received", type.name(), 90, "Resposta não confirmada", "execution", "provider-adapter");
      case SATELLITE_DECISION_CREATED ->
          bind("result_recorded", "SATELLITE_DECISION_CREATED", 110, "Resultado registrado", "result", "satellite-registry");
      case SATELLITE_RESPONSE_RETURNED ->
          bind("sync_completed", "SATELLITE_RESPONSE_RETURNED", 120, "Resposta devolvida", "result", "satellite-http");
      default -> null;
    };
  }

  public static Binding paymentObserved() {
    return bind("pay_observed", "PAYMENT_OBSERVED", 10, "Operação observada no ActionHub Pay", "discovery", "provider-adapter");
  }

  public static Binding paymentDiscovered() {
    return bind("pay_discovered", "PAYMENT_DISCOVERED", 20, "Descoberta pelo sincronismo", "discovery", "monitor-query");
  }

  public static Binding paymentCorrelated() {
    return bind("identity_correlated", "PAYMENT_CORRELATED", 30, "Identidade financeira correlacionada", "discovery", "monitor-query");
  }

  public static Binding paymentFinancial() {
    return bind("financial_state", "FINANCIAL_STATE", 40, "Estado financeiro registrado", "financial", "monitor-query");
  }

  public static Binding syncPaymentsCorrelated() {
    return bind("payments_correlated", "PAYMENTS_CORRELATED", 100, "Pagamentos correlacionados", "execution", "provider-adapter");
  }

  public static Binding syncProjectionsUpserted() {
    return bind("projections_upserted", "PROJECTIONS_UPSERTED", 105, "Projeções persistidas", "observe", "persistence-ports");
  }

  public static Binding syncCountsRecorded() {
    return bind("counts_recorded", "COUNTS_RECORDED", 108, "Contagens registradas", "result", "monitor-query");
  }

  public static Binding replayChecked() {
    return bind("replay_checked", "REPLAY_CHECK_PASSED", 22, "Replay e idempotência", "identity", "replay-guard");
  }

  public static String stageState(OperationalEventOutcome outcome, String reason, OperationalEventType type) {
    String value = reason == null ? "" : reason.trim().toUpperCase(Locale.ROOT);
    if (outcome == OperationalEventOutcome.REJECTED
        || value.equals("REJECTED")
        || value.equals("POLICY_REJECTED")
        || value.equals("NO_COMPANY_BINDING")
        || value.equals("NO_COMPATIBLE_CAPABILITY")
        || value.equals("INVALID_PAYLOAD")
        || value.equals("INVALID_CONTRACT_VERSION")
        || value.equals("MISSING_CONTEXT")
        || value.equals("AMBIGUOUS_OBJECTIVE")
        || value.equals("UNAUTHORIZED_SATELLITE")
        || value.equals("UNAUTHENTICATED")
        || value.equals("IDEMPOTENCY_CONFLICT")) {
      return "rejected";
    }
    if (outcome == OperationalEventOutcome.FAILURE
        || type == OperationalEventType.CAPABILITY_UNAVAILABLE
        || type == OperationalEventType.OUTBOUND_TIMEOUT
        || type == OperationalEventType.OUTBOUND_TRANSPORT_ERROR
        || value.equals("PROVIDER_UNAVAILABLE")
        || value.equals("FAILED")
        || value.equals("FAILURE")
        || value.equals("TECHNICAL_FAILURE")) {
      return "failed";
    }
    if (type == OperationalEventType.SATELLITE_RESPONSE_RETURNED
        || type == OperationalEventType.SATELLITE_DECISION_CREATED
        || type == OperationalEventType.PROVIDER_RESULT_RECEIVED
        || type == OperationalEventType.OUTBOUND_RESPONSE_RECEIVED
        || outcome == OperationalEventOutcome.SUCCESS) {
      return "completed";
    }
    if (MonitorArchitectureBackbone.STATE_NOT_USED.equalsIgnoreCase(value)
        || MonitorArchitectureBackbone.STATE_NOT_REACHED.equalsIgnoreCase(value)) {
      return value.toLowerCase(Locale.ROOT);
    }
    return "running";
  }

  public static String availability(java.util.List<MonitorJourneyStage> stages) {
    if (stages == null || stages.isEmpty()) {
      return MonitorJourneyStage.AVAILABILITY_UNAVAILABLE;
    }
    boolean terminal =
        stages.stream().anyMatch(stage -> TERMINAL_STAGE_IDS.contains(stage.stageId()));
    return terminal ? MonitorJourneyStage.AVAILABILITY_COMPLETE : MonitorJourneyStage.AVAILABILITY_PARTIAL;
  }

  public static String sanitizeDecision(String reason) {
    if (reason == null || reason.isBlank()) {
      return null;
    }
    String value = reason.trim();
    if (value.length() > 200) {
      return value.substring(0, 200);
    }
    String lower = value.toLowerCase(Locale.ROOT);
    if (lower.contains("token") || lower.contains("secret") || lower.contains("password")
        || lower.contains("cookie") || lower.contains("authorization")) {
      return null;
    }
    return value;
  }

  private static Binding pageBinding(Integer page, boolean received) {
    if (page == null) {
      return received
          ? bind("response_received", "PROVIDER_RESULT_RECEIVED", 90, "Adapter ActionHub Pay — resposta", "execution", "provider-adapter")
          : bind("adapter_selected", "OUTBOUND_REQUEST_STARTED", 60, "Rota ActionHub Pay sandbox", "resolution", "capability-catalog");
    }
    String id = "page_" + page;
    int order = 70 + Math.min(page, 20);
    String title = received ? "Página " + page + " recebida" : "Página " + page + " solicitada";
    return bind(id, received ? "PAGE_RECEIVED" : "PAGE_REQUESTED", order, title, "execution", "provider-adapter");
  }

  private static Binding bind(String id, String type, int order, String title, String definition, String component) {
    return new Binding(id, type, order, title, definition, component);
  }
}
