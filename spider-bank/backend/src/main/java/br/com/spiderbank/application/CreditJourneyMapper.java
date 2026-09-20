package br.com.spiderbank.application;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public final class CreditJourneyMapper {

  private CreditJourneyMapper() {}

  public static Map<String, Object> fromSatelliteResponse(Map<String, Object> body, String expectedCorrelationId) {
    if (body == null || body.isEmpty()) {
      throw new CreditJourneyException(
          "INTEGRATION_FAILURE", 502, "A resposta da Spider está vazia e não pode ser apresentada como resultado.");
    }
    Object correlation = body.get("correlationId");
    if (correlation == null || !expectedCorrelationId.equals(String.valueOf(correlation))) {
      throw new CreditJourneyException(
          "INTEGRATION_FAILURE",
          502,
          "A correlação devolvida pela Spider não confere com a interação enviada.");
    }
    String status = string(body.get("status"));
    if (status.isBlank()) {
      throw new CreditJourneyException(
          "INTEGRATION_FAILURE", 502, "A Spider devolveu uma resposta sem status contratual.");
    }
    Map<String, Object> view = new LinkedHashMap<>();
    view.put("status", publicStatus(status, body));
    view.put("headline", headline(status));
    view.put("explanation", explanation(body, status));
    view.put("watermark", string(body.get("watermark")));
    view.put("correlationId", expectedCorrelationId);
    view.put("decisionId", string(body.get("decisionId")));
    view.put("contextRef", string(body.get("contextRef")));
    view.put("requiredAction", string(body.get("requiredAction")));
    view.put("analysisComplete", false);
    view.put("simulationComplete", simulationComplete(body));
    view.put("creditDecision", "NONE");
    view.put("retryable", false);
    view.put("impediments", impediments(body));
    view.put("missingContext", listOfStrings(body.get("missingContext")));
    view.put("options", options(body));
    view.put("technical", technical(body, status));
    return view;
  }

  static String publicStatus(String status, Map<String, Object> body) {
    return switch (status) {
      case "PLAN_IMPEDED", "NO_COMPATIBLE_CAPABILITY" -> "ANALYSIS_BLOCKED";
      case "MISSING_CONTEXT" -> "NEEDS_CONTEXT";
      case "AMBIGUOUS" -> "NEEDS_CLARIFICATION";
      case "REJECTED" -> syntheticRejected(body) ? "SYNTHETIC_BLOCKED" : "POLICY_BLOCKED";
      case "PROVIDER_UNAVAILABLE" -> "TECHNICAL_UNAVAILABLE";
      case "PENDING" -> "SYNTHETIC_REVIEW";
      case "READY" -> "SIMULATION_SHOWN";
      default -> "INTEGRATION_RESULT";
    };
  }

  static String headline(String status) {
    return switch (status) {
      case "PLAN_IMPEDED", "NO_COMPATIBLE_CAPABILITY" ->
          "A análise não pode prosseguir nesta demonstração";
      case "MISSING_CONTEXT" -> "Falta contexto específico para continuar";
      case "AMBIGUOUS" -> "A declaração precisa ser esclarecida";
      case "REJECTED" -> "A jornada demonstrativa foi interrompida";
      case "PENDING" -> "Há uma pendência humana sintética";
      case "READY" -> "Simulação demonstrativa concluída";
      case "PROVIDER_UNAVAILABLE" -> "O executor simulado está indisponível";
      default -> "A Spider devolveu um resultado desta interação";
    };
  }

  private static String explanation(Map<String, Object> body, String status) {
    String explanation = string(body.get("explanation"));
    if (!explanation.isBlank()) {
      return explanation;
    }
    if ("PLAN_IMPEDED".equals(status) || "NO_COMPATIBLE_CAPABILITY".equals(status)) {
      return "A Spider selecionou o plano existente de capital de giro e devolveu impedimentos reais. Isso não é recusa de crédito.";
    }
    return "A Spider processou a interação e devolveu este resultado.";
  }

  private static List<Map<String, Object>> impediments(Map<String, Object> body) {
    Object summary = body.get("resultSummary");
    if (!(summary instanceof Map<?, ?> map)) {
      return List.of();
    }
    Object raw = map.get("impediments");
    if (!(raw instanceof List<?> list)) {
      return List.of();
    }
    List<Map<String, Object>> rows = new ArrayList<>();
    for (Object item : list) {
      if (item instanceof Map<?, ?> impediment) {
        Map<String, Object> row = new LinkedHashMap<>();
        row.put("sequence", impediment.get("sequence"));
        row.put("capabilityId", string(impediment.get("capabilityId")));
        row.put("availability", string(impediment.get("availability")));
        row.put("reason", string(impediment.get("reason")));
        row.put("title", humanCapability(string(impediment.get("capabilityId"))));
        rows.add(row);
      }
    }
    return rows;
  }

  static String humanCapability(String capabilityId) {
    return switch (capabilityId) {
      case "IDENTIFY_CUSTOMER" -> "Identificar o cliente autenticado";
      case "GET_CUSTOMER_PROFILE" -> "Consultar o perfil empresarial";
      case "CHECK_CUSTOMER_REGISTRATION" -> "Validar a situação cadastral";
      case "GET_CREDIT_PROFILE" -> "Consultar o perfil de crédito";
      case "FIND_ELIGIBLE_PRODUCTS" -> "Localizar produtos elegíveis";
      case "SIMULATE_WORKING_CAPITAL" -> "Simular capital de giro";
      case "PRESENT_OPTIONS" -> "Apresentar opções elegíveis";
      default -> capabilityId;
    };
  }

  private static boolean syntheticRejected(Map<String, Object> body) {
    Object summary = body.get("resultSummary");
    if (!(summary instanceof Map<?, ?> map)) {
      return false;
    }
    if (Boolean.TRUE.equals(map.get("providerDispatched"))) {
      return true;
    }
    Object steps = map.get("steps");
    if (steps instanceof List<?> list) {
      for (Object item : list) {
        if (item instanceof Map<?, ?> step) {
          Object executor = step.get("executor");
          if (executor != null
              && !"context-principal".equals(String.valueOf(executor))
              && !"internal-composition".equals(String.valueOf(executor))) {
            return true;
          }
        }
      }
    }
    return "WORKING_CAPITAL_EXECUTION".equals(String.valueOf(map.get("kind")));
  }

  private static boolean simulationComplete(Map<String, Object> body) {
    Object summary = body.get("resultSummary");
    return summary instanceof Map<?, ?> map && Boolean.TRUE.equals(map.get("simulationComplete"));
  }

  @SuppressWarnings("unchecked")
  private static Map<String, Object> options(Map<String, Object> body) {
    Object summary = body.get("resultSummary");
    if (!(summary instanceof Map<?, ?> map)) {
      return Map.of();
    }
    Object options = map.get("options");
    if (options instanceof Map<?, ?> raw) {
      return new LinkedHashMap<>((Map<String, Object>) raw);
    }
    return Map.of();
  }

  private static Map<String, Object> technical(Map<String, Object> body, String status) {
    Map<String, Object> technical = new LinkedHashMap<>();
    technical.put("spiderStatus", status);
    technical.put("contractVersion", body.get("contractVersion"));
    technical.put("spiderPath", body.get("spiderPath"));
    Object summary = body.get("resultSummary");
    if (summary instanceof Map<?, ?> map) {
      technical.put("intent", map.get("intent"));
      technical.put("planId", map.get("planId"));
      technical.put("providerDispatched", map.get("providerDispatched"));
    }
    return technical;
  }

  private static List<String> listOfStrings(Object value) {
    if (!(value instanceof List<?> list)) {
      return List.of();
    }
    List<String> values = new ArrayList<>();
    for (Object item : list) {
      if (item != null) {
        values.add(String.valueOf(item));
      }
    }
    return values;
  }

  private static String string(Object value) {
    return value == null ? "" : String.valueOf(value);
  }
}
